"""Authentication / OIDC routes: login, callback, logout, config, session."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from routes._deps import (
    SESSION_COOKIE,
    STATE_COOKIE,
    _cookie_secure,
    _decode_cookie,
    _encode_cookie,
    _is_safe_redirect_path,
    _legacy_oidc_enabled,
    _oidc_client,
    _oidc_enabled,
    _oidc_required,
    _random_token_urlsafe,
    _require_session,
    _session_from_request,
    _validate_project_id,
    is_feature_enabled,
    logger,
    resolve_secret,
)
from routes._models import SessionInfo, UIConfig

router = APIRouter()


def _resolve_post_login_redirect(state_payload: dict[str, Any]) -> str:
    import routes._deps as _deps_module

    counter = getattr(_deps_module, "post_login_landing_success_total", None)

    return_to = state_payload.get("return_to")
    if isinstance(return_to, str) and _is_safe_redirect_path(return_to):
        landing = return_to
        if counter:
            counter.add(1, {"flow": "return_to", "landing_route": landing})
        logger.info(
            "auth.post_login_landing",
            extra={"flow": "return_to", "requested_return_to": return_to, "landing_route": landing},
        )
        return landing

    project_id = state_payload.get("project_id")
    if project_id:
        landing = f"/app/projects/{project_id}"
        if counter:
            counter.add(1, {"flow": "project_id", "landing_route": landing})
        logger.info(
            "auth.post_login_landing",
            extra={"flow": "project_id", "project_id": project_id, "landing_route": landing},
        )
        return landing

    landing = "/app"
    if counter:
        counter.add(1, {"flow": "default", "landing_route": landing})
    logger.info("auth.post_login_landing", extra={"flow": "default", "landing_route": landing})
    return landing


async def _exchange_code_for_token(code: str) -> dict[str, Any]:
    token_url = _oidc_required("OIDC_TOKEN_URL")
    client_id = _oidc_required("OIDC_CLIENT_ID")
    client_secret = resolve_secret(os.getenv("OIDC_CLIENT_SECRET"))
    redirect_uri = _oidc_required("OIDC_REDIRECT_URI")
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    if client_secret:
        payload["client_secret"] = client_secret
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(token_url, data=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("OIDC token exchange failed: status=%s", exc.response.status_code)
        raise HTTPException(status_code=502, detail="OIDC token exchange failed") from exc
    except httpx.RequestError as exc:
        logger.error("OIDC token exchange request error: %s", exc)
        raise HTTPException(status_code=502, detail="OIDC provider unreachable") from exc


async def _decode_id_token(id_token: str) -> dict[str, Any]:
    jwks_url = _oidc_required("OIDC_JWKS_URL")
    audience = os.getenv("OIDC_AUDIENCE")
    issuer = os.getenv("OIDC_ISSUER")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("OIDC JWKS fetch failed: status=%s", exc.response.status_code)
        raise HTTPException(status_code=502, detail="OIDC JWKS fetch failed") from exc
    except httpx.RequestError as exc:
        logger.error("OIDC JWKS request error: %s", exc)
        raise HTTPException(status_code=502, detail="OIDC JWKS endpoint unreachable") from exc
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


def _ui_feature_flags() -> dict[str, bool]:
    environment = os.getenv("ENVIRONMENT", "dev")
    return {
        "agent_run_ui": is_feature_enabled("agent_run_ui", environment=environment, default=False),
        "multimodal_intake": is_feature_enabled(
            "multimodal_intake", environment=environment, default=False
        ),
        "duplicate_resolution": is_feature_enabled(
            "duplicate_resolution", environment=environment, default=False
        ),
        "predictive_alerts": is_feature_enabled(
            "predictive_alerts", environment=environment, default=False
        ),
        "resource_optimization": is_feature_enabled(
            "resource_optimization", environment=environment, default=False
        ),
        "multi_agent_collab": is_feature_enabled(
            "multi_agent_collab", environment=environment, default=False
        ),
        "autonomous_deliverables": is_feature_enabled(
            "autonomous_deliverables", environment=environment, default=False
        ),
        "unified_dashboards": is_feature_enabled(
            "unified_dashboards", environment=environment, default=False
        ),
    }


from urllib.parse import urlencode  # noqa: E402


@router.get("/config", response_model=UIConfig)
async def config() -> UIConfig:
    return UIConfig(
        api_gateway_url=os.getenv("API_GATEWAY_URL", "http://api-gateway:8000"),
        workflow_service_url=os.getenv("WORKFLOW_SERVICE_URL", "http://localhost:8082"),
        oidc_enabled=_oidc_enabled(),
        login_url="/login",
        logout_url="/logout",
        feature_flags=_ui_feature_flags(),
    )


@router.get("/session", response_model=SessionInfo)
async def session_info(request: Request) -> SessionInfo:
    session = _session_from_request(request)
    if not session:
        return SessionInfo(authenticated=False)
    return SessionInfo(
        authenticated=True,
        subject=session.get("subject"),
        tenant_id=session.get("tenant_id"),
        roles=session.get("roles"),
        permissions=session.get("permissions"),
    )


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    if not _oidc_enabled():
        if _legacy_oidc_enabled():
            auth_url = _oidc_required("OIDC_AUTH_URL")
            client_id = _oidc_required("OIDC_CLIENT_ID")
            redirect_uri = _oidc_required("OIDC_REDIRECT_URI")
            state = _random_token_urlsafe(16)
            nonce = _random_token_urlsafe(16)
            project_id = _validate_project_id(request.query_params.get("project_id"))
            return_to = request.query_params.get("return_to")
            if return_to and not _is_safe_redirect_path(return_to):
                return_to = None
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
                STATE_COOKIE,
                _encode_cookie(
                    {
                        "state": state,
                        "nonce": nonce,
                        "project_id": project_id,
                        "return_to": return_to,
                    },
                    600,
                ),
                httponly=True,
                secure=_cookie_secure(),
                samesite="lax",
            )
            return response
        auth_dev_mode = os.getenv("AUTH_DEV_MODE", "false").lower() in {"1", "true", "yes"}
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if auth_dev_mode and environment in {"dev", "development", "local", "test"}:
            return RedirectResponse(url="/app")
        raise HTTPException(status_code=500, detail="OIDC not configured")

    client = _oidc_client()
    discovery = await client.discover()
    state = _random_token_urlsafe(16)
    nonce = _random_token_urlsafe(16)
    project_id = _validate_project_id(request.query_params.get("project_id"))
    return_to = request.query_params.get("return_to")
    if return_to and not _is_safe_redirect_path(return_to):
        return_to = None
    params = {
        "client_id": client.client_id,
        "response_type": "code",
        "scope": client.scope,
        "redirect_uri": client.redirect_uri,
        "state": state,
        "nonce": nonce,
    }
    response = RedirectResponse(url=f"{discovery.authorization_endpoint}?{urlencode(params)}")
    response.set_cookie(
        STATE_COOKIE,
        _encode_cookie(
            {"state": state, "nonce": nonce, "project_id": project_id, "return_to": return_to}, 600
        ),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )
    return response


@router.get("/oidc/callback")
async def oidc_callback(request: Request) -> RedirectResponse:
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OIDC callback parameters")
    state_cookie = request.cookies.get(STATE_COOKIE)
    state_payload = _decode_cookie(state_cookie) if state_cookie else None
    if not state_payload or state_payload.get("state") != state:
        raise HTTPException(status_code=400, detail="Invalid login state")
    if _oidc_enabled():
        client = _oidc_client()
        token_response = await client.exchange_code(code)
    elif _legacy_oidc_enabled():
        token_response = await _exchange_code_for_token(code)
        client = None
    else:
        raise HTTPException(status_code=500, detail="OIDC not configured")
    id_token = token_response.get("id_token")
    access_token = token_response.get("access_token")
    if not id_token or not access_token:
        raise HTTPException(status_code=401, detail="OIDC token response missing tokens")
    if client:
        claims = await client.verify_id_token(id_token, state_payload.get("nonce"))
    else:
        claims = await _decode_id_token(id_token)
    tenant_claim = os.getenv("OIDC_TENANT_CLAIM", "tenant_id")
    roles_claim = os.getenv("OIDC_ROLES_CLAIM", "roles")
    tenant_id = claims.get(tenant_claim)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="OIDC token missing tenant claim")
    roles = claims.get(roles_claim) or []
    if isinstance(roles, str):
        roles = [roles]
    session_payload = {
        "access_token": access_token,
        "id_token": id_token,
        "tenant_id": tenant_id,
        "subject": claims.get("sub"),
        "roles": roles,
    }
    redirect_target = _resolve_post_login_redirect(state_payload)
    response = RedirectResponse(url=redirect_target)
    response.set_cookie(
        SESSION_COOKIE,
        _encode_cookie(session_payload, 8 * 60 * 60),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )
    response.delete_cookie(STATE_COOKIE)
    return response


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    return await oidc_callback(request)


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    session = _session_from_request(request) or {}
    response = RedirectResponse(url="/")
    discovery = None
    if _oidc_enabled():
        client = _oidc_client()
        discovery = await client.discover()
    if discovery and discovery.end_session_endpoint and session.get("id_token"):
        params = {"id_token_hint": session["id_token"]}
        response = RedirectResponse(url=f"{discovery.end_session_endpoint}?{urlencode(params)}")
    elif _legacy_oidc_enabled():
        logout_url = os.getenv("OIDC_LOGOUT_URL")
        if logout_url:
            response = RedirectResponse(url=logout_url)
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(STATE_COOKIE)
    return response


@router.get("/api/status")
async def api_status(request: Request) -> dict[str, Any]:
    session = _require_session(request)
    api_gateway_url = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{api_gateway_url}/v1/status",
            headers={
                "Authorization": f"Bearer {session['access_token']}",
                "X-Tenant-ID": session["tenant_id"],
            },
        )
        response.raise_for_status()
        return response.json()
