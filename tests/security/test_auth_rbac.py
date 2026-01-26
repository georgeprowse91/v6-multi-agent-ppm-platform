from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import jwt
from fastapi.testclient import TestClient


def _make_token(role: str) -> str:
    return jwt.encode(
        {
            "sub": "user-123",
            "roles": [role],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": "tenant-alpha",
        },
        "test-secret",
        algorithm="HS256",
    )


def _client():
    from api.main import app

    return TestClient(app)


def test_missing_auth_headers(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    response = client.get("/api/v1/status")
    assert response.status_code == 401


def test_missing_tenant_header(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = _make_token("portfolio_admin")
    response = client.get("/api/v1/status", headers={"Authorization": f"Bearer {token}"})
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
        "/api/v1/status",
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
            "/api/v1/query",
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
    mock_orchestrator.process_query = AsyncMock(return_value={"success": True})

    with patch("api.main.orchestrator", mock_orchestrator):
        response = client.post(
            "/api/v1/query",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
            json={"query": "test", "classification": "internal"},
        )
    assert response.status_code == 200


def test_tenant_mismatch(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = _make_token("portfolio_admin")

    response = client.get(
        "/api/v1/status",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-beta"},
    )
    assert response.status_code == 403
