import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    return TestClient(main.app)


def test_get_dependency_map_returns_nodes_and_links(client, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", "tenant-a")
    response = client.get("/api/dependency-map/program-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["program_id"] == "program-1"
    assert payload["nodes"]
    assert payload["links"]
    assert {"id", "label", "type"}.issubset(payload["nodes"][0])


def test_get_program_roadmap_returns_phases_and_milestones(client, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", "tenant-a")
    response = client.get("/api/program-roadmap/program-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["program_id"] == "program-1"
    assert payload["phases"]
    assert payload["milestones"]
    assert {"id", "name", "start", "end"}.issubset(payload["phases"][0])
