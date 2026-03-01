from __future__ import annotations

from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

pytest.importorskip("slowapi")


def _make_token(role: str, tenant_id: str = "tenant-alpha") -> str:
    return jwt.encode(
        {
            "sub": "user-123",
            "roles": [role],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": tenant_id,
        },
        "test-secret",
        algorithm="HS256",
    )


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    monkeypatch.setenv("AGENT_CONFIG_STORE_PATH", str(tmp_path / "agent_config.json"))
    monkeypatch.setenv(
        "AGENT_CONFIG_DATABASE_URL", f"sqlite:///{tmp_path / 'agent_config_rbac.db'}"
    )
    from agent_config_service import reset_store_instance
    from api.main import app

    reset_store_instance()
    return TestClient(app)


def test_agent_config_requires_auth(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.patch("/v1/agents/config/agent-01-intent-router-agent", json={"enabled": False})
    assert response.status_code == 401


def test_agent_config_rejects_insufficient_role(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    token = _make_token("TEAM_MEMBER")
    response = client.patch(
        "/v1/agents/config/agent-01-intent-router-agent",
        json={"enabled": False},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
    )
    assert response.status_code == 403
