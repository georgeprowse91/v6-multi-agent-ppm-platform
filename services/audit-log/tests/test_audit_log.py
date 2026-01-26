from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("audit_log_main", MODULE_PATH)
module = module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "audit-log"


def test_ingest_and_fetch_event() -> None:
    storage_path = (
        Path(__file__).resolve().parents[3]
        / "services"
        / "audit-log"
        / "storage"
        / "audit-events.jsonl"
    )
    if storage_path.exists():
        storage_path.unlink()

    payload = {
        "id": "evt-123",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": {"id": "user-1", "type": "user"},
        "action": "project.create",
        "resource": {"id": "proj-9", "type": "project"},
        "outcome": "success",
        "metadata": {"ip": "127.0.0.1"},
        "trace_id": "trace-1",
        "correlation_id": "corr-1",
    }

    response = client.post("/audit/events", json=payload)
    assert response.status_code == 200
    assert response.json()["event"]["id"] == "evt-123"

    fetch = client.get("/audit/events/evt-123")
    assert fetch.status_code == 200
    assert fetch.json()["action"] == "project.create"

    assert storage_path.exists()
    with storage_path.open("r", encoding="utf-8") as handle:
        assert json.loads(handle.readline())["id"] == "evt-123"
