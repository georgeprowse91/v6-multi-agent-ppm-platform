from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[2] / "services" / "data-lineage-service"
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("data_lineage_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
SRC_PATH = str(SERVICE_ROOT / "src")
sys.path.insert(0, SRC_PATH)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
if SRC_PATH in sys.path:
    sys.path.remove(SRC_PATH)


def _configure_auth(monkeypatch, tenant_id: str = "tenant-qa") -> None:
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def test_lineage_event_ingest_and_quality_summary(monkeypatch, tmp_path) -> None:
    store_path = tmp_path / "lineage.json"
    monkeypatch.setenv("DATA_LINEAGE_STORE_PATH", str(store_path))
    monkeypatch.setenv("LINEAGE_MASK_SALT", "unit-test-salt")
    _configure_auth(monkeypatch)

    with TestClient(module.app) as client:
        payload = {
            "tenant_id": "tenant-qa",
            "connector": "jira",
            "source": {"system": "jira", "object": "project", "record_id": "P-1"},
            "target": {"schema": "project", "record_id": "PROJ-1"},
            "transformations": ["jira.project.name -> project.name"],
            "entity_type": "project",
            "entity_payload": {
                "project": {
                    "id": "proj-1",
                    "name": "Atlas",
                    "status": "active",
                }
            },
        }
        response = client.post("/lineage/events", json=payload, headers={"X-Tenant-ID": "tenant-qa"})
        assert response.status_code == 200
        data = response.json()
        assert data["quality"] is not None
        assert "project-required-fields" in data["quality"]["rules_checked"]

        list_response = client.get("/lineage/events", headers={"X-Tenant-ID": "tenant-qa"})
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        graph_response = client.get("/lineage/graph", headers={"X-Tenant-ID": "tenant-qa"})
        assert graph_response.status_code == 200
        graph = graph_response.json()
        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1

        quality_response = client.get(
            "/quality/summary", headers={"X-Tenant-ID": "tenant-qa"}
        )
        assert quality_response.status_code == 200
        summary = quality_response.json()
        assert summary["total_events"] == 1
        assert summary["average_score"] >= 0
