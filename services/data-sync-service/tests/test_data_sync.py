from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("data_sync_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def _auth_headers(monkeypatch, tenant_id: str = "tenant-alpha") -> dict[str, str]:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["integration_service"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": tenant_id,
        },
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def test_run_sync_creates_status(monkeypatch, tmp_path) -> None:
    status_path = tmp_path / "status.json"
    monkeypatch.setenv("DATA_SYNC_STATUS_PATH", str(status_path))

    response = client.post(
        "/sync/run",
        json={"connector": "jira", "dry_run": True},
        headers=_auth_headers(monkeypatch),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"

    status_response = client.get(
        f"/sync/status/{payload['job_id']}", headers=_auth_headers(monkeypatch)
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "queued"
