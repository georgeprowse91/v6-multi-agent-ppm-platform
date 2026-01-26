from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

WEB_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = WEB_ROOT / "static"

SESSION_COOKIE = "ppm_session"
SESSION_STORE: dict[str, dict[str, Any]] = {}

app = FastAPI(title="PPM Web Console", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "web-ui"


class UIConfig(BaseModel):
    api_gateway_url: str
    workflow_engine_url: str
    oidc_enabled: bool
    login_url: str
    logout_url: str


class SessionInfo(BaseModel):
    authenticated: bool
    subject: str | None = None
    tenant_id: str | None = None
    roles: list[str] | None = None


class WorkflowStartRequest(BaseModel):
    workflow_id: str


class WorkflowStartResponse(BaseModel):
    run_id: str
    workflow_id: str
    tenant_id: str
    status: str
    created_at: str
    updated_at: str


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _oidc_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise HTTPException(status_code=500, detail=f"Missing OIDC setting: {name}")
    return value


def _oidc_optional(name: str) -> str | None:
    return os.getenv(name)


def _session_from_request(request: Request) -> dict[str, Any] | None:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return None
    return SESSION_STORE.get(session_id)


def _require_session(request: Request) -> dict[str, Any]:
    session = _session_from_request(request)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def _oidc_enabled() -> bool:
    return bool(
        os.getenv("OIDC_CLIENT_ID") and os.getenv("OIDC_AUTH_URL") and os.getenv("OIDC_TOKEN_URL")
    )


async def _exchange_code_for_token(code: str) -> dict[str, Any]:
    token_url = _oidc_required("OIDC_TOKEN_URL")
    client_id = _oidc_required("OIDC_CLIENT_ID")
    client_secret = _oidc_optional("OIDC_CLIENT_SECRET")
    redirect_uri = _oidc_required("OIDC_REDIRECT_URI")

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(token_url, data=payload)
        response.raise_for_status()
        return response.json()


async def _decode_id_token(id_token: str) -> dict[str, Any]:
    jwks_url = _oidc_optional("OIDC_JWKS_URL")
    audience = _oidc_optional("OIDC_AUDIENCE")
    issuer = _oidc_optional("OIDC_ISSUER")
    insecure = os.getenv("OIDC_INSECURE_SKIP_VERIFY", "false").lower() == "true"

    if not jwks_url:
        if insecure:
            return jwt.decode(id_token, options={"verify_signature": False})
        raise HTTPException(
            status_code=500, detail="OIDC_JWKS_URL is required for token verification"
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        jwks = response.json()

    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header.get("kid")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail="OIDC signing key not found")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    return jwt.decode(
        id_token,
        public_key,
        algorithms=[unverified_header.get("alg", "RS256")],
        audience=audience,
        issuer=issuer,
        options={"verify_aud": bool(audience), "verify_iss": bool(issuer)},
    )


@app.get("/config", response_model=UIConfig)
async def config() -> UIConfig:
    return UIConfig(
        api_gateway_url=os.getenv("API_GATEWAY_URL", "http://localhost:8000"),
        workflow_engine_url=os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8082"),
        oidc_enabled=_oidc_enabled(),
        login_url="/login",
        logout_url="/logout",
    )


@app.get("/session", response_model=SessionInfo)
async def session_info(request: Request) -> SessionInfo:
    session = _session_from_request(request)
    if not session:
        return SessionInfo(authenticated=False)
    return SessionInfo(
        authenticated=True,
        subject=session.get("subject"),
        tenant_id=session.get("tenant_id"),
        roles=session.get("roles"),
    )


@app.get("/login")
async def login() -> RedirectResponse:
    if not _oidc_enabled():
        raise HTTPException(status_code=500, detail="OIDC not configured")

    auth_url = _oidc_required("OIDC_AUTH_URL")
    client_id = _oidc_required("OIDC_CLIENT_ID")
    redirect_uri = _oidc_required("OIDC_REDIRECT_URI")

    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    session_id = secrets.token_urlsafe(24)
    SESSION_STORE[session_id] = {"state": state, "nonce": nonce}

    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": os.getenv("OIDC_SCOPE", "openid profile email"),
        "redirect_uri": redirect_uri,
        "state": state,
        "nonce": nonce,
    }
    response = RedirectResponse(url=f"{auth_url}?{urlencode(params)}")
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        secure=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
        samesite="lax",
    )
    return response


@app.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OIDC callback parameters")

    session = _session_from_request(request)
    if not session or session.get("state") != state:
        raise HTTPException(status_code=400, detail="Invalid login state")

    token_response = await _exchange_code_for_token(code)
    id_token = token_response.get("id_token")
    access_token = token_response.get("access_token")
    if not id_token or not access_token:
        raise HTTPException(status_code=401, detail="OIDC token response missing tokens")

    claims = await _decode_id_token(id_token)
    tenant_claim = os.getenv("OIDC_TENANT_CLAIM", "tenant_id")
    roles_claim = os.getenv("OIDC_ROLES_CLAIM", "roles")
    tenant_id = claims.get(tenant_claim)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="OIDC token missing tenant claim")

    roles = claims.get(roles_claim) or []
    if isinstance(roles, str):
        roles = [roles]

    session.update(
        {
            "access_token": access_token,
            "id_token": id_token,
            "tenant_id": tenant_id,
            "subject": claims.get("sub"),
            "roles": roles,
        }
    )

    return RedirectResponse(url="/")


@app.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        SESSION_STORE.pop(session_id, None)

    logout_url = _oidc_optional("OIDC_LOGOUT_URL")
    response = RedirectResponse(url=logout_url or "/")
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/api/status")
async def api_status(request: Request) -> dict[str, Any]:
    session = _require_session(request)
    api_gateway_url = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{api_gateway_url}/api/v1/status",
            headers={
                "Authorization": f"Bearer {session['access_token']}",
                "X-Tenant-ID": session["tenant_id"],
            },
        )
        response.raise_for_status()
        return response.json()


@app.post("/api/workflows/start", response_model=WorkflowStartResponse)
async def api_start_workflow(request: Request, payload: WorkflowStartRequest) -> dict[str, Any]:
    session = _require_session(request)
    workflow_url = os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8082")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{workflow_url}/workflows/start",
            headers={
                "Authorization": f"Bearer {session['access_token']}",
                "X-Tenant-ID": session["tenant_id"],
            },
            json={
                "workflow_id": payload.workflow_id,
                "tenant_id": session["tenant_id"],
                "classification": "internal",
                "payload": {"request": "run"},
                "actor": {
                    "id": session.get("subject") or "ui-user",
                    "type": "user",
                    "roles": session.get("roles") or ["portfolio_admin"],
                },
            },
        )
        response.raise_for_status()
        return response.json()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8501, reload=False)
