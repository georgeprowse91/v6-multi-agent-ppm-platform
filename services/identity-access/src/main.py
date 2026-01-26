from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx
import jwt
from fastapi import FastAPI, HTTPException
from jwt import InvalidTokenError
from pydantic import BaseModel

logger = logging.getLogger("identity-access")
logging.basicConfig(level=logging.INFO)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "identity-access"


class AuthValidateRequest(BaseModel):
    token: str


class AuthValidateResponse(BaseModel):
    active: bool
    subject: str | None = None
    claims: dict[str, Any] | None = None


class JwksCache:
    def __init__(self) -> None:
        self.jwks: dict[str, Any] | None = None
        self.fetched_at: float = 0

    def get(self) -> dict[str, Any] | None:
        if self.jwks and (time.time() - self.fetched_at) < 300:
            return self.jwks
        return None

    def set(self, jwks: dict[str, Any]) -> None:
        self.jwks = jwks
        self.fetched_at = time.time()


JWKS_CACHE = JwksCache()

app = FastAPI(title="Identity Access Service", version="0.1.0")


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _get_env(name: str) -> str | None:
    return os.getenv(name)


@app.post("/auth/validate", response_model=AuthValidateResponse)
async def validate_token(request: AuthValidateRequest) -> AuthValidateResponse:
    jwt_secret = _get_env("IDENTITY_JWT_SECRET")
    jwks_url = _get_env("IDENTITY_JWKS_URL")
    audience = _get_env("IDENTITY_AUDIENCE")
    issuer = _get_env("IDENTITY_ISSUER")

    try:
        if jwks_url:
            claims = _verify_with_jwks(request.token, jwks_url, audience, issuer)
        elif jwt_secret:
            claims = jwt.decode(
                request.token,
                jwt_secret,
                algorithms=["HS256"],
                audience=audience,
                issuer=issuer,
                options={"verify_aud": bool(audience), "verify_iss": bool(issuer)},
            )
        else:
            raise HTTPException(status_code=500, detail="JWT configuration missing")
    except InvalidTokenError as exc:
        logger.warning("token_validation_failed", extra={"error": str(exc)})
        return AuthValidateResponse(active=False)

    return AuthValidateResponse(active=True, subject=claims.get("sub"), claims=claims)


def _verify_with_jwks(token: str, jwks_url: str, audience: str | None, issuer: str | None) -> dict[str, Any]:
    cached = JWKS_CACHE.get()
    if cached is None:
        response = httpx.get(jwks_url, timeout=5.0)
        response.raise_for_status()
        cached = response.json()
        JWKS_CACHE.set(cached)

    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    keys = cached.get("keys", [])
    key = next((k for k in keys if k.get("kid") == kid), None)
    if not key:
        raise InvalidTokenError("JWKS key not found")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    return jwt.decode(
        token,
        public_key,
        algorithms=[unverified_header.get("alg", "RS256")],
        audience=audience,
        issuer=issuer,
        options={"verify_aud": bool(audience), "verify_iss": bool(issuer)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
