from __future__ import annotations

import logging
import os
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

from auth import authenticate_request, validate_token  # noqa: E402
from common.env_validation import reject_placeholder_secrets  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.api_governance import (  # noqa: E402
    apply_api_governance,
    version_response_payload,
)
from security.secrets import resolve_secret  # noqa: E402

from packages.version import API_VERSION

logger = logging.getLogger("auth-service")
logging.basicConfig(level=logging.INFO)

reject_placeholder_secrets(
    service_name="auth-service",
    environment=os.getenv("ENVIRONMENT"),
    secret_vars={
        k: v
        for k, v in {
            "AUTH_CLIENT_SECRET": resolve_secret(os.getenv("AUTH_CLIENT_SECRET", "")),
        }.items()
        if v
    },
)

app = FastAPI(title="Auth Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
configure_tracing("auth-service")
configure_metrics("auth-service")
app.add_middleware(TraceMiddleware, service_name="auth-service")
app.add_middleware(RequestMetricsMiddleware, service_name="auth-service")
apply_api_governance(app, service_name="auth-service")


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "auth-service"
    dependencies: dict[str, str] = Field(default_factory=dict)


class LoginRequest(BaseModel):
    grant_type: str = Field("authorization_code", description="OAuth2 grant type")
    code: str | None = None
    redirect_uri: str | None = None
    username: str | None = None
    password: str | None = None
    scope: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str
    scope: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


class LogoutRequest(BaseModel):
    token: str | None = None
    token_type_hint: str | None = None


class TokenResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    id_token: str | None = None
    scope: str | None = None
    raw: dict[str, Any] | None = None


class AuthValidateRequest(BaseModel):
    token: str


class AuthValidateResponse(BaseModel):
    active: bool
    subject: str | None = None
    claims: dict[str, Any] | None = None


class AuthContextResponse(BaseModel):
    tenant_id: str
    subject: str
    roles: list[str]
    claims: dict[str, Any]


_OIDC_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _oidc_cache_ttl_seconds() -> int:
    raw_value = _get_env("AUTH_OIDC_CACHE_TTL_SECONDS")
    if not raw_value:
        return 300
    try:
        return max(0, int(raw_value))
    except ValueError:
        logger.warning("Invalid AUTH_OIDC_CACHE_TTL_SECONDS value: %s", raw_value)
        return 300


def _oidc_cache_max_entries() -> int:
    raw_value = _get_env("AUTH_OIDC_CACHE_MAX_ENTRIES")
    if not raw_value:
        return 16
    try:
        return max(0, int(raw_value))
    except ValueError:
        logger.warning("Invalid AUTH_OIDC_CACHE_MAX_ENTRIES value: %s", raw_value)
        return 16


def _prune_oidc_cache(now: float, ttl_seconds: int, max_entries: int) -> None:
    if ttl_seconds <= 0 or max_entries <= 0:
        _OIDC_CACHE.clear()
        return
    expired_keys = [
        discovery_url
        for discovery_url, entry in _OIDC_CACHE.items()
        if now - entry["fetched_at"] >= ttl_seconds
    ]
    for discovery_url in expired_keys:
        _OIDC_CACHE.pop(discovery_url, None)
    while len(_OIDC_CACHE) > max_entries:
        _OIDC_CACHE.popitem(last=False)


def _get_env(name: str, fallback: str | None = None) -> str | None:
    value = resolve_secret(os.getenv(name))
    if value:
        return value
    if fallback:
        return resolve_secret(os.getenv(fallback))
    return None


async def _load_oidc_config(discovery_url: str) -> dict[str, Any]:
    ttl_seconds = _oidc_cache_ttl_seconds()
    max_entries = _oidc_cache_max_entries()
    now = time.monotonic()
    _prune_oidc_cache(now, ttl_seconds, max_entries)
    cached = _OIDC_CACHE.get(discovery_url)
    if cached and now - cached["fetched_at"] < ttl_seconds:
        _OIDC_CACHE.move_to_end(discovery_url)
        return cached["data"]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(discovery_url)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "OIDC discovery failed for %s (%s)",
            discovery_url,
            type(exc).__name__,
        )
        raise
    _OIDC_CACHE[discovery_url] = {"data": data, "fetched_at": now}
    _OIDC_CACHE.move_to_end(discovery_url)
    _prune_oidc_cache(now, ttl_seconds, max_entries)
    return data


async def _resolve_token_endpoint() -> str:
    token_url = _get_env("AUTH_TOKEN_URL")
    if token_url:
        return token_url
    discovery_url = _get_env("AUTH_OIDC_DISCOVERY_URL", "IDENTITY_OIDC_DISCOVERY_URL")
    issuer = _get_env("AUTH_ISSUER", "IDENTITY_ISSUER")
    if discovery_url or issuer:
        discovery_url = discovery_url or f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        oidc_config = await _load_oidc_config(discovery_url)
        token_url = oidc_config.get("token_endpoint")
    if not token_url:
        raise HTTPException(status_code=500, detail="Token endpoint not configured")
    return token_url


async def _resolve_revocation_endpoint() -> str | None:
    revocation_url = _get_env("AUTH_REVOCATION_URL")
    if revocation_url:
        return revocation_url
    discovery_url = _get_env("AUTH_OIDC_DISCOVERY_URL", "IDENTITY_OIDC_DISCOVERY_URL")
    issuer = _get_env("AUTH_ISSUER", "IDENTITY_ISSUER")
    if discovery_url or issuer:
        discovery_url = discovery_url or f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        oidc_config = await _load_oidc_config(discovery_url)
        return oidc_config.get("revocation_endpoint")
    return None


async def _resolve_logout_endpoint() -> str | None:
    logout_url = _get_env("AUTH_LOGOUT_URL")
    if logout_url:
        return logout_url
    discovery_url = _get_env("AUTH_OIDC_DISCOVERY_URL", "IDENTITY_OIDC_DISCOVERY_URL")
    issuer = _get_env("AUTH_ISSUER", "IDENTITY_ISSUER")
    if discovery_url or issuer:
        discovery_url = discovery_url or f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        oidc_config = await _load_oidc_config(discovery_url)
        return oidc_config.get("end_session_endpoint")
    return None


def _client_credentials(
    request_client_id: str | None, request_client_secret: str | None
) -> tuple[str, str | None]:
    client_id = request_client_id or _get_env("AUTH_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="Auth client ID not configured")
    client_secret = request_client_secret or _get_env("AUTH_CLIENT_SECRET")
    return client_id, client_secret


async def _exchange_token(payload: dict[str, Any]) -> dict[str, Any]:
    token_url = await _resolve_token_endpoint()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    dependencies = {"oidc_discovery": "unknown", "token_endpoint": "unknown"}
    token_url = _get_env("AUTH_TOKEN_URL")
    discovery_url = _get_env("AUTH_OIDC_DISCOVERY_URL", "IDENTITY_OIDC_DISCOVERY_URL")
    issuer = _get_env("AUTH_ISSUER", "IDENTITY_ISSUER")
    if discovery_url or issuer:
        discovery_url = discovery_url or f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        try:
            oidc_config = await _load_oidc_config(discovery_url)
            dependencies["oidc_discovery"] = "ok"
            token_url = token_url or oidc_config.get("token_endpoint")
        except (ValueError, httpx.HTTPError):
            dependencies["oidc_discovery"] = "down"
    else:
        dependencies["oidc_discovery"] = "degraded"

    dependencies["token_endpoint"] = "ok" if token_url else "down"
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("auth-service")


@api_router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    client_id, client_secret = _client_credentials(request.client_id, request.client_secret)
    payload: dict[str, Any] = {
        "grant_type": request.grant_type,
        "client_id": client_id,
    }
    if client_secret:
        payload["client_secret"] = client_secret
    if request.scope or os.getenv("AUTH_SCOPE"):
        payload["scope"] = request.scope or os.getenv("AUTH_SCOPE")

    if request.grant_type == "authorization_code":
        if not request.code:
            raise HTTPException(status_code=400, detail="Authorization code is required")
        payload["code"] = request.code
        if request.redirect_uri:
            payload["redirect_uri"] = request.redirect_uri
    elif request.grant_type == "password":
        if not request.username or not request.password:
            raise HTTPException(status_code=400, detail="Username and password required")
        payload["username"] = request.username
        payload["password"] = request.password
    elif request.grant_type == "client_credentials":
        pass
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant type")

    token_response = await _exchange_token(payload)
    payload_fields = {
        key: token_response.get(key) for key in TokenResponse.model_fields if key != "raw"
    }
    return TokenResponse(**payload_fields, raw=token_response)


@api_router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest) -> TokenResponse:
    client_id, client_secret = _client_credentials(request.client_id, request.client_secret)
    payload: dict[str, Any] = {
        "grant_type": "refresh_token",
        "refresh_token": request.refresh_token,
        "client_id": client_id,
    }
    if client_secret:
        payload["client_secret"] = client_secret
    if request.scope or os.getenv("AUTH_SCOPE"):
        payload["scope"] = request.scope or os.getenv("AUTH_SCOPE")

    token_response = await _exchange_token(payload)
    payload_fields = {
        key: token_response.get(key) for key in TokenResponse.model_fields if key != "raw"
    }
    return TokenResponse(**payload_fields, raw=token_response)


@api_router.post("/auth/logout")
async def logout(request: LogoutRequest) -> dict[str, str]:
    revocation_endpoint = await _resolve_revocation_endpoint()
    logout_endpoint = await _resolve_logout_endpoint()
    token = request.token
    if not token:
        return {"status": "no_token"}

    if revocation_endpoint:
        client_id, client_secret = _client_credentials(None, None)
        payload = {"token": token, "client_id": client_id}
        if client_secret:
            payload["client_secret"] = client_secret
        if request.token_type_hint:
            payload["token_type_hint"] = request.token_type_hint
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                revocation_endpoint,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
        return {"status": "revoked"}

    if logout_endpoint:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(logout_endpoint, data={"token": token})
            response.raise_for_status()
        return {"status": "logged_out"}

    return {"status": "unsupported"}


@api_router.post("/auth/validate", response_model=AuthValidateResponse)
async def validate_auth(request: AuthValidateRequest) -> AuthValidateResponse:
    try:
        claims = await validate_token(request.token)
    except HTTPException:
        return AuthValidateResponse(active=False)
    return AuthValidateResponse(active=True, subject=claims.get("sub"), claims=claims)


@api_router.get("/auth/me", response_model=AuthContextResponse)
async def whoami(request: Request) -> AuthContextResponse:
    auth_context = await authenticate_request(request)
    return AuthContextResponse(
        tenant_id=auth_context.tenant_id,
        subject=auth_context.subject,
        roles=auth_context.roles,
        claims=auth_context.claims,
    )


app.include_router(api_router)
