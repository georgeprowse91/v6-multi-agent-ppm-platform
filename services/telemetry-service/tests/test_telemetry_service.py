from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("telemetry_service_main", MODULE_PATH)
module = module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "telemetry-service"


def test_telemetry_ingest() -> None:
    payload = {
        "source": "api-gateway",
        "type": "log",
        "payload": {"message": "hello"},
    }
    response = client.post("/telemetry/ingest", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["ingested"] is True
    assert "correlation_id" in body
