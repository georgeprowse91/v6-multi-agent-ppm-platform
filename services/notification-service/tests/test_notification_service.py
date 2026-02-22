from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("notification_service_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
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


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "notification-service"


def test_send_notification(monkeypatch) -> None:
    payload = {
        "template": "welcome",
        "variables": {
            "recipient_name": "Morgan",
            "event_name": "Stage Gate Approved",
            "event_time": "2025-01-01T00:00:00Z",
        },
        "channel": "stdout",
        "recipient": "morgan@ppm.georgeprowse91.com",
    }
    response = client.post(
        "/v1/notifications/send", json=payload, headers=_auth_headers(monkeypatch)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "delivered"
    assert "Stage Gate Approved" in body["rendered"]
