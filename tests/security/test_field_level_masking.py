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


def test_field_masking_blocks_restricted_fields(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = _make_token("project_manager")

    _METADATA = {
        "agent_id": "test-agent",
        "catalog_id": "test-agent",
        "timestamp": "2024-01-01T00:00:00Z",
        "correlation_id": "test-corr-mask",
    }

    mock_orchestrator = MagicMock()
    mock_orchestrator.initialized = True
    mock_orchestrator.process_query = AsyncMock(
        return_value={
            "success": True,
            "data": {
                "project": {"budget": 50000, "risk_rating": "high"},
                "portfolio": {"strategic_score": 92},
            },
            "metadata": _METADATA,
        }
    )

    with patch("api.main.orchestrator", mock_orchestrator):
        response = client.post(
            "/v1/query",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
            json={"query": "status", "classification": "internal"},
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["project"]["budget"] == 50000
    assert data["project"]["risk_rating"] == "REDACTED"
    assert data["portfolio"]["strategic_score"] == "REDACTED"


def test_field_masking_allows_privileged_fields(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client()
    token = _make_token("portfolio_admin")

    _METADATA = {
        "agent_id": "test-agent",
        "catalog_id": "test-agent",
        "timestamp": "2024-01-01T00:00:00Z",
        "correlation_id": "test-corr-priv",
    }

    mock_orchestrator = MagicMock()
    mock_orchestrator.initialized = True
    mock_orchestrator.process_query = AsyncMock(
        return_value={
            "success": True,
            "data": {
                "project": {"budget": 50000, "risk_rating": "high"},
                "portfolio": {"strategic_score": 92},
            },
            "metadata": _METADATA,
        }
    )

    with patch("api.main.orchestrator", mock_orchestrator):
        response = client.post(
            "/v1/query",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
            json={"query": "status", "classification": "internal"},
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["project"]["budget"] == 50000
    assert data["project"]["risk_rating"] == "high"
    assert data["portfolio"]["strategic_score"] == 92
