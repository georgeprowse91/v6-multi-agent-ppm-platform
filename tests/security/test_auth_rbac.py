from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import jwt
from fastapi.testclient import TestClient


def _make_token(role: str, *, extra_claims: dict | None = None) -> str:
    claims = {
        "sub": "user-123",
        "roles": [role],
        "aud": "ppm-platform",
        "iss": "https://issuer.example.com",
        "tenant_id": "tenant-alpha",
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, "test-secret", algorithm="HS256")


def _client():
    from api.main import app

    return TestClient(app)


def test_missing_auth_headers(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    response = client.get("/v1/status")
    assert response.status_code == 401


def test_missing_tenant_header(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = _make_token("portfolio_admin")
    response = client.get("/v1/status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_missing_tenant_claim(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
        },
        "test-secret",
        algorithm="HS256",
    )
    response = client.get(
        "/v1/status",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
    )
    assert response.status_code == 403


def test_rbac_blocks_insufficient_role(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = _make_token("analyst")

    mock_orchestrator = MagicMock()
    mock_orchestrator.initialized = True
    mock_orchestrator.process_query = AsyncMock(return_value={"success": True})

    with patch("api.main.orchestrator", mock_orchestrator):
        response = client.post(
            "/v1/query",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
            json={"query": "test", "classification": "restricted"},
        )
    assert response.status_code == 403


def test_rbac_allows_portfolio_admin(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = _make_token("portfolio_admin")

    mock_orchestrator = MagicMock()
    mock_orchestrator.initialized = True
    mock_orchestrator.process_query = AsyncMock(
        return_value={
            "success": True,
            "data": {"message": "ok"},
            "metadata": {
                "agent_id": "router",
                "catalog_id": "intent-router-agent",
                "timestamp": "2024-01-01T00:00:00Z",
                "correlation_id": "corr-123",
            },
        }
    )

    with patch("api.main.orchestrator", mock_orchestrator):
        response = client.post(
            "/v1/query",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
            json={"query": "test", "classification": "internal"},
        )
    assert response.status_code == 200


def test_tenant_mismatch(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = _make_token("portfolio_admin")

    response = client.get(
        "/v1/status",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-beta"},
    )
    assert response.status_code == 403


def test_invalid_jwt_signature_rejected(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "tenant_id": "tenant-alpha",
        },
        "wrong-secret",
        algorithm="HS256",
    )
    response = client.get(
        "/v1/status",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
    )
    assert response.status_code == 401


def test_expired_jwt_rejected(monkeypatch) -> None:
    import time

    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "tenant_id": "tenant-alpha",
            "exp": int(time.time()) - 3600,
        },
        "test-secret",
        algorithm="HS256",
    )
    response = client.get(
        "/v1/status",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
    )
    assert response.status_code == 401


def test_empty_roles_blocked_for_write(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = jwt.encode(
        {
            "sub": "user-empty-roles",
            "roles": [],
            "tenant_id": "tenant-alpha",
        },
        "test-secret",
        algorithm="HS256",
    )
    response = client.post(
        "/v1/query",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
        json={"query": "test"},
    )
    assert response.status_code == 403


def test_identity_access_validation(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_ACCESS_URL", "https://idp.example.com")
    client = _client()

    class MockResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    class MockAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):
            return MockResponse(
                {
                    "active": True,
                    "claims": {
                        "sub": "user-123",
                        "roles": ["portfolio_admin"],
                        "tenant_id": "tenant-alpha",
                    },
                }
            )

    with patch("api.middleware.security.httpx.AsyncClient", MockAsyncClient):
        response = client.get(
            "/v1/status",
            headers={"Authorization": "Bearer oidc-token", "X-Tenant-ID": "tenant-alpha"},
        )
    assert response.status_code == 200
