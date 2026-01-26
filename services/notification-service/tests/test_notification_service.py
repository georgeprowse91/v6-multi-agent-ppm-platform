from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("notification_service_main", MODULE_PATH)
module = module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "notification-service"


def test_send_notification() -> None:
    payload = {
        "template": "welcome",
        "variables": {
            "recipient_name": "Morgan",
            "event_name": "Stage Gate Approved",
            "event_time": "2025-01-01T00:00:00Z",
        },
        "channel": "stdout",
        "recipient": "morgan@example.com",
    }
    response = client.post("/notifications/send", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "delivered"
    assert "Stage Gate Approved" in body["rendered"]
