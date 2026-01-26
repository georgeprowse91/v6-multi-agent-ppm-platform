from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
from fastapi.testclient import TestClient


def _load_app(path: Path, module_name: str):
    spec = spec_from_file_location(module_name, path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.app


def _identity_client():
    path = Path(__file__).resolve().parents[2] / "services" / "identity-access" / "src" / "main.py"
    return TestClient(_load_app(path, "identity_access_main"))


def _gateway_client():
    from api.main import app

    return TestClient(app)


def _workflow_client():
    path = Path(__file__).resolve().parents[2] / "apps" / "workflow-engine" / "src" / "main.py"
    return TestClient(_load_app(path, "workflow_engine_main"))


def test_end_to_end_workflow(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": "tenant-alpha",
        },
        "test-secret",
        algorithm="HS256",
    )

    identity = _identity_client()
    identity_response = identity.post("/auth/validate", json={"token": token})
    assert identity_response.status_code == 200
    assert identity_response.json()["active"] is True

    mock_orchestrator = MagicMock()
    mock_orchestrator.initialized = True
    mock_orchestrator.process_query = AsyncMock(
        return_value={"success": True, "data": {"ok": True}}
    )

    gateway = _gateway_client()
    with patch("api.main.orchestrator", mock_orchestrator):
        response = gateway.post(
            "/api/v1/query",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
            json={"query": "Start workflow", "classification": "internal"},
        )
    assert response.status_code == 200

    workflow = _workflow_client()
    workflow_response = workflow.post(
        "/workflows/start",
        json={
            "workflow_id": "intake-triage",
            "tenant_id": "tenant-alpha",
            "classification": "internal",
            "payload": {"request": "upgrade"},
            "actor": {"id": "user-123", "type": "user", "roles": ["portfolio_admin"]},
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
    )
    assert workflow_response.status_code == 200
    assert workflow_response.json()["status"] == "running"
