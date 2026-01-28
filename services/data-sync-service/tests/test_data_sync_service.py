from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("data_sync_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "data-sync-service"


def test_sync_run_returns_rules() -> None:
    response = client.post("/sync/run", json={"connector": "jira", "dry_run": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert "ds-001" in payload["planned_rules"]
