from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
from fastapi.testclient import TestClient


def _load_app():
    module_path = (
        Path(__file__).resolve().parents[2] / "apps" / "workflow-engine" / "src" / "main.py"
    )
    spec = spec_from_file_location("workflow_engine_main", module_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.app


def test_workflow_persistence(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "workflow.db"
    monkeypatch.setenv("WORKFLOW_DB_PATH", str(db_path))
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
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"}

    app = _load_app()
    client = TestClient(app)

    response = client.post(
        "/workflows/start",
        json={
            "workflow_id": "intake-triage",
            "tenant_id": "tenant-alpha",
            "classification": "internal",
            "payload": {"request": "run"},
            "actor": {"id": "user-123", "type": "user", "roles": ["portfolio_admin"]},
        },
        headers=headers,
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    fetch = client.get(f"/workflows/{run_id}", headers=headers)
    assert fetch.status_code == 200
    assert fetch.json()["run_id"] == run_id
