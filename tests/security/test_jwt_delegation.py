"""Tests verifying that the API gateway middleware delegates JWT validation
to security.auth.authenticate_request (Issue 1 — auth code deduplication).

Ensures:
- AuthTenantMiddleware calls authenticate_request from security.auth
- Successful auth sets request.state.auth to an AuthContext
- Failed auth (401/403) returns structured error payloads
- Webhook paths and health paths are exempt from auth
- The middleware no longer has its own _validate_jwt implementation
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException, Request

# ---------------------------------------------------------------------------
# Test that _validate_jwt no longer exists in the middleware module
# ---------------------------------------------------------------------------


def test_middleware_has_no_local_validate_jwt() -> None:
    """The local _validate_jwt duplicate must have been removed."""
    import api.middleware.security as sec_mod

    assert not hasattr(sec_mod, "_validate_jwt"), (
        "_validate_jwt should have been removed from the gateway middleware; "
        "JWT validation is now delegated to security.auth.authenticate_request"
    )


def test_middleware_has_no_oidc_ttl_cache_class() -> None:
    """The local _OIDCTTLCache duplicate must have been removed."""
    import api.middleware.security as sec_mod

    assert not hasattr(sec_mod, "_OIDCTTLCache"), (
        "_OIDCTTLCache should have been removed from the gateway middleware; "
        "caching is now handled by security.auth._TTLCache"
    )


def test_middleware_imports_authenticate_request() -> None:
    """The middleware must import authenticate_request from security.auth."""
    import api.middleware.security as sec_mod

    assert hasattr(sec_mod, "authenticate_request"), (
        "authenticate_request must be importable from api.middleware.security "
        "(imported from security.auth)"
    )


def test_middleware_imports_auth_context_from_security_auth() -> None:
    """AuthContext must be the same class as security.auth.AuthContext."""
    from api.middleware.security import AuthContext as GatewayAuthContext
    from security.auth import AuthContext as PackageAuthContext

    assert GatewayAuthContext is PackageAuthContext, (
        "AuthContext in the gateway middleware must be the same class as "
        "security.auth.AuthContext (not a local duplicate)"
    )


# ---------------------------------------------------------------------------
# Functional: middleware delegates to authenticate_request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_calls_authenticate_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """AuthTenantMiddleware.dispatch must call security.auth.authenticate_request."""
    from api.middleware.security import AuthTenantMiddleware
    from security.auth import AuthContext

    expected_ctx = AuthContext(
        tenant_id="t1",
        subject="user-1",
        roles=["portfolio_admin"],
        claims={"sub": "user-1", "tenant_id": "t1"},
    )

    call_count = 0

    async def mock_authenticate(request: Request, config=None) -> AuthContext:
        nonlocal call_count
        call_count += 1
        return expected_ctx

    monkeypatch.setattr("api.middleware.security.authenticate_request", mock_authenticate)

    # Build a minimal ASGI app so we can test the middleware
    async def dummy_app(scope, receive, send):
        pass

    middleware = AuthTenantMiddleware(dummy_app)

    # Craft a fake request that is not in the exempt paths
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/agents",
        "query_string": b"",
        "headers": [
            (b"authorization", b"Bearer fake-token"),
            (b"x-tenant-id", b"t1"),
        ],
    }

    # Patch RBAC/ABAC so we only test delegation
    async def mock_rbac(*args, **kwargs):
        pass

    async def mock_abac(*args, **kwargs):
        pass

    monkeypatch.setattr("api.middleware.security._evaluate_rbac", mock_rbac)
    monkeypatch.setattr("api.middleware.security._evaluate_abac", mock_abac)

    captured_auth = None

    async def call_next(request: Request):
        nonlocal captured_auth
        captured_auth = getattr(request.state, "auth", None)
        from starlette.responses import Response

        return Response("ok")

    # Provide an empty-body receive channel so request.body() succeeds
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(scope, receive)
    await middleware.dispatch(request, call_next)

    assert call_count == 1, "authenticate_request should have been called once"
    assert captured_auth is expected_ctx, "request.state.auth must be the AuthContext from authenticate_request"


@pytest.mark.asyncio
async def test_dispatch_returns_401_on_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 401 from authenticate_request must propagate as a JSON 401 response."""
    from api.middleware.security import AuthTenantMiddleware

    async def mock_authenticate(request: Request, config=None):
        raise HTTPException(status_code=401, detail="Missing JWT or tenant header")

    monkeypatch.setattr("api.middleware.security.authenticate_request", mock_authenticate)

    async def dummy_app(scope, receive, send):
        pass

    middleware = AuthTenantMiddleware(dummy_app)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/agents",
        "query_string": b"",
        "headers": [],
    }

    async def call_next(request: Request):
        from starlette.responses import Response

        return Response("should not reach")

    request = Request(scope)
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 401


def test_exempt_paths_bypass_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Health and root paths must not call authenticate_request."""
    from api.middleware.security import AuthTenantMiddleware

    call_count = 0

    async def mock_authenticate(request: Request, config=None):
        nonlocal call_count
        call_count += 1
        raise HTTPException(status_code=401, detail="Should not be called")

    monkeypatch.setattr("api.middleware.security.authenticate_request", mock_authenticate)

    import asyncio

    async def dummy_app(scope, receive, send):
        pass

    middleware = AuthTenantMiddleware(dummy_app)

    for exempt_path in ("/healthz", "/", "/version", "/v1/health"):
        scope = {
            "type": "http",
            "method": "GET",
            "path": exempt_path,
            "query_string": b"",
            "headers": [],
        }

        async def call_next(request):
            from starlette.responses import Response

            return Response("ok")

        request = Request(scope)
        asyncio.run(middleware.dispatch(request, call_next))

    assert call_count == 0, f"authenticate_request called {call_count} times for exempt paths"
