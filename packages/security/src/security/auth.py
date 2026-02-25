from __future__ import annotations

import json
import logging
import os
import threading
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

import httpx
import jwt

try:
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
except ModuleNotFoundError:  # pragma: no cover - fallback for constrained local smoke envs

    class RSAPublicKey:  # type: ignore[no-redef]
        pass


from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from jwt import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from security.errors import error_payload
from security.iam import map_groups_to_roles

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
    oidc_discovery_url: str | None
    tenant_claim: str
    roles_claim: str


def _load_config() -> AuthConfig:
    return AuthConfig(
        identity_access_url=os.getenv("AUTH_SERVICE_URL") or os.getenv("IDENTITY_ACCESS_URL"),
        jwt_secret=os.getenv("IDENTITY_JWT_SECRET"),
        jwks_url=os.getenv("IDENTITY_JWKS_URL"),
        audience=os.getenv("IDENTITY_AUDIENCE"),
        issuer=os.getenv("IDENTITY_ISSUER"),
        oidc_discovery_url=os.getenv("IDENTITY_OIDC_DISCOVERY_URL"),
        tenant_claim=os.getenv("IDENTITY_TENANT_CLAIM", "tenant_id"),
        roles_claim=os.getenv("IDENTITY_ROLES_CLAIM", "roles"),
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
    iam_roles = map_groups_to_roles(claims)
    combined = list(roles) + iam_roles
    return list(dict.fromkeys(combined))


import time as _time

# Cache TTL in seconds (default 5 minutes)
_CACHE_TTL = float(os.getenv("AUTH_CACHE_TTL_SECONDS", "300"))
_CACHE_MAX_SIZE = int(os.getenv("AUTH_CACHE_MAX_ENTRIES", "128"))


@dataclass
class _CacheEntry:
    value: dict[str, Any]
    inserted_at: float
    last_fetched_at: float


class _TTLCache:
    def __init__(self, ttl_seconds: float, max_size: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_size = max(1, max_size)
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

    def _evict_stale_locked(self, now: float) -> None:
        stale_keys = [
            key
            for key, entry in self._entries.items()
            if now - entry.inserted_at >= self._ttl_seconds
        ]
        for key in stale_keys:
            self._entries.pop(key, None)

    def get(self, key: str) -> dict[str, Any] | None:
        now = _time.time()
        with self._lock:
            self._evict_stale_locked(now)
            entry = self._entries.get(key)
            if not entry:
                return None
            entry.last_fetched_at = now
            self._entries.move_to_end(key)
            return entry.value

    def set(self, key: str, value: dict[str, Any]) -> None:
        now = _time.time()
        with self._lock:
            self._evict_stale_locked(now)
            self._entries[key] = _CacheEntry(value=value, inserted_at=now, last_fetched_at=now)
            self._entries.move_to_end(key)

            while len(self._entries) > self._max_size:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_OIDC_CONFIG_CACHE = _TTLCache(ttl_seconds=_CACHE_TTL, max_size=_CACHE_MAX_SIZE)
_JWKS_CACHE = _TTLCache(ttl_seconds=_CACHE_TTL, max_size=_CACHE_MAX_SIZE)


async def _load_oidc_config(discovery_url: str) -> dict[str, Any]:
    cached = _OIDC_CONFIG_CACHE.get(discovery_url)
    if cached:
        return cached
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(discovery_url)
        response.raise_for_status()
        data = cast(dict[str, Any], response.json())
    _OIDC_CONFIG_CACHE.set(discovery_url, data)
    return data


async def _load_jwks(jwks_url: str) -> dict[str, Any]:
    cached = _JWKS_CACHE.get(jwks_url)
    if cached:
        return cached
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        data = cast(dict[str, Any], response.json())
    _JWKS_CACHE.set(jwks_url, data)
    return data


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
        jwks_url = config.jwks_url
        issuer = config.issuer
        # Only attempt OIDC discovery when no jwt_secret is configured (RS256 path).
        # If jwt_secret is set the caller intends HS256 validation; deriving a
        # discovery URL from issuer would cause unnecessary network calls.
        if not jwks_url and not config.jwt_secret and (config.oidc_discovery_url or issuer):
            discovery_url = config.oidc_discovery_url or (
                f"{issuer.rstrip('/')}/.well-known/openid-configuration" if issuer else None
            )
            if discovery_url:
                oidc_config = await _load_oidc_config(discovery_url)
                jwks_url = oidc_config.get("jwks_uri")
                issuer = issuer or oidc_config.get("issuer")

        if jwks_url:
            jwks = await _load_jwks(jwks_url)
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
                    options={
                        "verify_aud": bool(config.audience),
                        "verify_iss": bool(issuer),
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


def clear_auth_caches() -> None:
    """Clear all in-process authentication caches.

    Forces fresh OIDC discovery document and JWKS fetches on the next request.
    Call this after an LLM API key or IdP JWKS rotation to ensure the process
    picks up new credentials without requiring a restart.
    """
    _OIDC_CONFIG_CACHE.clear()
    _JWKS_CACHE.clear()


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


class AuthTenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, exempt_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self._config: AuthConfig = _load_config()
        self._exempt_paths: set[str] = exempt_paths or {"/healthz"}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path in self._exempt_paths:
            return await call_next(request)

        try:
            auth_context = await authenticate_request(request, self._config)
        except HTTPException as exc:
            message = exc.detail if isinstance(exc.detail, str) else "Request failed"
            payload = error_payload(
                message=message, code=f"http_{exc.status_code}", details=exc.detail
            )
            return JSONResponse(status_code=exc.status_code, content=payload)

        request.state.auth = auth_context
        return await call_next(request)
