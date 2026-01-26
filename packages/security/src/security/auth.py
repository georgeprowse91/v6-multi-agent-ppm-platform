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
from fastapi.responses import JSONResponse
from jwt import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("security-auth")


@dataclass
class AuthContext:
    tenant_id: str
    subject: str
    roles: list[str]
    claims: dict[str, Any]


@dataclass
class AuthConfig:
    identity_access_url: str | None
    jwt_secret: str | None
    jwks_url: str | None
    audience: str | None
    issuer: str | None
    tenant_claim: str
    roles_claim: str


def _load_config() -> AuthConfig:
    return AuthConfig(
        identity_access_url=os.getenv("IDENTITY_ACCESS_URL"),
        jwt_secret=os.getenv("IDENTITY_JWT_SECRET"),
        jwks_url=os.getenv("IDENTITY_JWKS_URL"),
        audience=os.getenv("IDENTITY_AUDIENCE"),
        issuer=os.getenv("IDENTITY_ISSUER"),
        tenant_claim=os.getenv("IDENTITY_TENANT_CLAIM", "tenant_id"),
        roles_claim=os.getenv("IDENTITY_ROLES_CLAIM", "roles"),
    )


def _normalize_roles(claims: dict[str, Any], roles_claim: str) -> list[str]:
    roles = claims.get(roles_claim) or claims.get("role") or []
    if isinstance(roles, str):
        roles = [roles]
    return list(roles)


async def _validate_jwt(token: str, config: AuthConfig) -> dict[str, Any]:
    if config.identity_access_url:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{config.identity_access_url}/auth/validate", json={"token": token}
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("active"):
                raise HTTPException(status_code=401, detail="Invalid token")
            return data.get("claims") or {}

    try:
        if config.jwks_url:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(config.jwks_url)
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
                    issuer=config.issuer,
                    options={
                        "verify_aud": bool(config.audience),
                        "verify_iss": bool(config.issuer),
                    },
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

    claim_tenant = claims.get(config.tenant_claim)
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


class AuthTenantMiddleware(BaseHTTPMiddleware):
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
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        request.state.auth = auth_context
        return await call_next(request)
