from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, cast

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import HTTPException, Request
from jwt import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware

from security.errors import error_payload

logger = logging.getLogger("auth-service")


@dataclass
class AuthContext:
    tenant_id: str
    subject: str
    roles: list[str]
    claims: dict[str, Any]


@dataclass
class AuthConfig:
    jwt_secret: str | None
    jwks_url: str | None
    audience: str | None
    issuer: str | None
    oidc_discovery_url: str | None
    tenant_claim: str
    roles_claim: str


def _get_env(name: str, fallback: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    if fallback:
        return os.getenv(fallback)
    return None


def _load_config() -> AuthConfig:
    return AuthConfig(
        jwt_secret=_get_env("AUTH_JWT_SECRET", "IDENTITY_JWT_SECRET"),
        jwks_url=_get_env("AUTH_JWKS_URL", "IDENTITY_JWKS_URL"),
        audience=_get_env("AUTH_AUDIENCE", "IDENTITY_AUDIENCE"),
        issuer=_get_env("AUTH_ISSUER", "IDENTITY_ISSUER"),
        oidc_discovery_url=_get_env("AUTH_OIDC_DISCOVERY_URL", "IDENTITY_OIDC_DISCOVERY_URL"),
        tenant_claim=os.getenv("AUTH_TENANT_CLAIM")
        or os.getenv("IDENTITY_TENANT_CLAIM")
        or "tenant_id",
        roles_claim=os.getenv("AUTH_ROLES_CLAIM")
        or os.getenv("IDENTITY_ROLES_CLAIM")
        or "roles",
    )


def _get_claim(claims: dict[str, Any], path: str) -> Any:
    current: Any = claims
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _normalize_roles(claims: dict[str, Any], roles_claim: str) -> list[str]:
    roles = _get_claim(claims, roles_claim) or claims.get("role") or claims.get("groups") or []
    if isinstance(roles, str):
        roles = [role.strip() for role in roles.replace(",", " ").split() if role.strip()]
    return list(dict.fromkeys(roles))


_OIDC_CONFIG_CACHE: dict[str, dict[str, Any]] = {}


async def _load_oidc_config(discovery_url: str) -> dict[str, Any]:
    if discovery_url in _OIDC_CONFIG_CACHE:
        return _OIDC_CONFIG_CACHE[discovery_url]
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(discovery_url)
        response.raise_for_status()
        data = response.json()
    _OIDC_CONFIG_CACHE[discovery_url] = data
    return data


async def _validate_jwt(token: str, config: AuthConfig) -> dict[str, Any]:
    try:
        jwks_url = config.jwks_url
        issuer = config.issuer
        if not jwks_url and (config.oidc_discovery_url or issuer):
            discovery_url = config.oidc_discovery_url or (
                f"{issuer.rstrip('/')}/.well-known/openid-configuration" if issuer else None
            )
            if discovery_url:
                oidc_config = await _load_oidc_config(discovery_url)
                jwks_url = oidc_config.get("jwks_uri")
                issuer = issuer or oidc_config.get("issuer")

        if jwks_url:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                jwks = response.json()
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
            if not key:
                raise HTTPException(status_code=401, detail="Invalid token key")
            public_key = cast(RSAPublicKey, jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key)))
            return cast(
                dict[str, Any],
                jwt.decode(
                    token,
                    public_key,
                    algorithms=[unverified_header.get("alg", "RS256")],
                    audience=config.audience,
                    issuer=issuer,
                    options={"verify_aud": bool(config.audience), "verify_iss": bool(issuer)},
                ),
            )

        if not config.jwt_secret:
            raise HTTPException(status_code=500, detail="JWT validation configuration missing")

        return cast(
            dict[str, Any],
            jwt.decode(
                token,
                config.jwt_secret,
                algorithms=["HS256"],
                audience=config.audience,
                issuer=config.issuer,
                options={"verify_aud": bool(config.audience), "verify_iss": bool(config.issuer)},
            ),
        )
    except InvalidTokenError as exc:
        logger.warning("token_validation_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=401, detail="Invalid token") from exc


async def validate_token(token: str, config: AuthConfig | None = None) -> dict[str, Any]:
    config = config or _load_config()
    return await _validate_jwt(token, config)


async def authenticate_request(request: Request, config: AuthConfig | None = None) -> AuthContext:
    auth_header = request.headers.get("Authorization", "")
    token = (
        auth_header.replace("Bearer ", "", 1).strip() if auth_header.startswith("Bearer ") else None
    )
    tenant_id = request.headers.get("X-Tenant-ID")

    if not token or not tenant_id:
        raise HTTPException(status_code=401, detail="Missing JWT or tenant header")

    config = config or _load_config()
    claims = await _validate_jwt(token, config)

    claim_tenant = _get_claim(claims, config.tenant_claim)
    if not claim_tenant:
        raise HTTPException(status_code=403, detail="Tenant claim missing")
    if claim_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    roles = _normalize_roles(claims, config.roles_claim)

    return AuthContext(
        tenant_id=tenant_id,
        subject=claims.get("sub", "unknown"),
        roles=roles,
        claims=claims,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exempt_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self._config = _load_config()
        self._exempt_paths = exempt_paths or {"/healthz"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._exempt_paths:
            return await call_next(request)
        try:
            auth_context = await authenticate_request(request, self._config)
        except HTTPException as exc:
            from fastapi.responses import JSONResponse

            message = exc.detail if isinstance(exc.detail, str) else "Request failed"
            payload = error_payload(message=message, code=f"http_{exc.status_code}", details=exc.detail)
            return JSONResponse(status_code=exc.status_code, content=payload)
        request.state.auth = auth_context
        return await call_next(request)
