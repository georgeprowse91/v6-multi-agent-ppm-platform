from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

pytest.importorskip("cryptography")

from security import auth
from security.auth import AuthConfig

FIXED_NOW = 1_700_000_000
HS256_SECRET = "unit-test-secret"


@pytest.fixture(autouse=True)
def _clear_auth_caches() -> None:
    auth._OIDC_CONFIG_CACHE.clear()
    auth._JWKS_CACHE.clear()


@pytest.fixture
def jwt_config() -> AuthConfig:
    return AuthConfig(
        identity_access_url=None,
        jwt_secret=HS256_SECRET,
        jwks_url=None,
        audience="ppm-platform",
        issuer="https://issuer.example",
        oidc_discovery_url=None,
        tenant_claim="tenant_id",
        roles_claim="roles",
    )


def _build_request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/status",
        "headers": [(k.lower().encode("utf-8"), v.encode("utf-8")) for k, v in headers.items()],
    }
    return Request(scope)


def _make_hs256_token(
    *, tenant_id: str = "tenant-alpha", exp: int | None = None, secret: str = HS256_SECRET
) -> str:
    claims: dict[str, Any] = {
        "sub": "user-123",
        "tenant_id": tenant_id,
        "roles": ["Portfolio_Admin"],
        "aud": "ppm-platform",
        "iss": "https://issuer.example",
        "iat": FIXED_NOW,
    }
    if exp is not None:
        claims["exp"] = exp
    return jwt.encode(claims, secret, algorithm="HS256")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("label", "token_factory", "expected_status"),
    [
        ("valid_token", lambda: _make_hs256_token(exp=FIXED_NOW + 3600), None),
        ("expired_token", lambda: _make_hs256_token(exp=FIXED_NOW - 3600), 401),
        ("malformed_token", lambda: "this-is-not-a-jwt", 401),
        (
            "wrong_signature",
            lambda: _make_hs256_token(exp=FIXED_NOW + 3600, secret="wrong-secret"),
            401,
        ),
    ],
)
async def test_validate_jwt_matrix(
    label: str,
    token_factory: Callable[[], str],
    expected_status: int | None,
    jwt_config: AuthConfig,
) -> None:
    token = token_factory()

    if expected_status is None:
        claims = await auth._validate_jwt(token, jwt_config)
        assert claims["sub"] == "user-123", label
        return

    with pytest.raises(HTTPException) as exc:
        await auth._validate_jwt(token, jwt_config)
    assert exc.value.status_code == expected_status, label


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("claims", "tenant_header", "expected_status", "expected_detail"),
    [
        (
            {
                "sub": "user-123",
                "roles": ["viewer"],
                "aud": "ppm-platform",
                "iss": "https://issuer.example",
            },
            "tenant-alpha",
            403,
            "Tenant claim missing",
        ),
        (
            {
                "sub": "user-123",
                "roles": ["viewer"],
                "tenant_id": "tenant-alpha",
                "aud": "ppm-platform",
                "iss": "https://issuer.example",
            },
            "tenant-beta",
            403,
            "Tenant mismatch",
        ),
    ],
)
async def test_authenticate_request_claim_failures(
    claims: dict[str, Any],
    tenant_header: str,
    expected_status: int,
    expected_detail: str,
    jwt_config: AuthConfig,
) -> None:
    token = jwt.encode(claims, HS256_SECRET, algorithm="HS256")
    request = _build_request({"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_header})

    with pytest.raises(HTTPException) as exc:
        await auth.authenticate_request(request, jwt_config)

    assert exc.value.status_code == expected_status
    assert exc.value.detail == expected_detail


@pytest.mark.parametrize(
    ("claims", "iam_roles", "expected_roles"),
    [
        ({"roles": []}, [], []),
        ({"roles": ["Admin", "admin", "EDITOR", "Admin"]}, [], ["Admin", "admin", "EDITOR"]),
        (
            {"roles": "analyst, Analyst ANALYST"},
            ["reviewer", "reviewer"],
            ["analyst", "Analyst", "ANALYST", "reviewer"],
        ),
    ],
)
def test_normalize_roles_edge_cases(
    monkeypatch: pytest.MonkeyPatch,
    claims: dict[str, Any],
    iam_roles: list[str],
    expected_roles: list[str],
) -> None:
    monkeypatch.setattr(auth, "map_groups_to_roles", lambda _claims: iam_roles)
    assert auth._normalize_roles(claims, "roles") == expected_roles


@dataclass
class _MockResponse:
    payload: dict[str, Any]
    status_code: int = 200

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://idp.example")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("mock failure", request=request, response=response)

    def json(self) -> dict[str, Any]:
        return self.payload


class _MockAsyncClient:
    def __init__(
        self, routes: dict[str, _MockResponse], calls: list[str], *args: Any, **kwargs: Any
    ) -> None:
        self._routes = routes
        self._calls = calls

    async def __aenter__(self) -> _MockAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str) -> _MockResponse:
        self._calls.append(url)
        return self._routes[url]


@pytest.mark.asyncio
async def test_oidc_helpers_load_discovery_and_jwks(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    routes = {
        "https://issuer.example/.well-known/openid-configuration": _MockResponse(
            {"issuer": "https://issuer.example", "jwks_uri": "https://issuer.example/jwks"}
        ),
        "https://issuer.example/jwks": _MockResponse({"keys": [{"kid": "kid-1"}]}),
    }
    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _MockAsyncClient(routes, calls, *args, **kwargs),
    )

    oidc_config = await auth._load_oidc_config(
        "https://issuer.example/.well-known/openid-configuration"
    )
    jwks = await auth._load_jwks("https://issuer.example/jwks")

    assert oidc_config["jwks_uri"] == "https://issuer.example/jwks"
    assert jwks["keys"][0]["kid"] == "kid-1"
    assert calls == [
        "https://issuer.example/.well-known/openid-configuration",
        "https://issuer.example/jwks",
    ]


@pytest.mark.asyncio
async def test_oidc_helper_failure_path_raises_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    routes = {
        "https://issuer.example/.well-known/openid-configuration": _MockResponse(
            {}, status_code=503
        )
    }
    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _MockAsyncClient(routes, [], *args, **kwargs),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth._load_oidc_config("https://issuer.example/.well-known/openid-configuration")
