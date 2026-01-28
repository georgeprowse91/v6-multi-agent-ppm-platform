import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
from workspace_state_store import WorkspaceStateStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    main.workspace_state_store = WorkspaceStateStore(tmp_path / "workspace_state.json")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def test_default_state_created_per_tenant(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get("/api/workspace/demo-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == "tenant-a"
    assert payload["project_id"] == "demo-1"
    assert payload["current_canvas_tab"] == "document"
    assert payload["activity_completion"] == {}

    _set_tenant(monkeypatch, "tenant-b")
    response = client.get("/api/workspace/demo-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == "tenant-b"
    assert payload["current_canvas_tab"] == "document"


def test_select_persists_canvas_tab(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": None,
            "current_activity_id": None,
            "current_canvas_tab": "timeline",
            "methodology": "agile",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["current_canvas_tab"] == "timeline"
    assert payload["methodology"] == "agile"

    response = client.get("/api/workspace/demo-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["current_canvas_tab"] == "timeline"


def test_activity_completion_persists(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/activity-completion",
        json={"activity_id": "activity-1", "completed": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["activity_completion"] == {"activity-1": True}

    response = client.get("/api/workspace/demo-1")
    payload = response.json()
    assert payload["activity_completion"]["activity-1"] is True


def test_tenant_isolation(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": "stage-1",
            "current_activity_id": "activity-1",
            "current_canvas_tab": "tree",
            "methodology": None,
        },
    )
    assert response.status_code == 200

    _set_tenant(monkeypatch, "tenant-b")
    response = client.get("/api/workspace/demo-1")
    payload = response.json()
    assert payload["tenant_id"] == "tenant-b"
    assert payload["current_canvas_tab"] == "document"
    assert payload["current_stage_id"] is None


def test_validation_rejects_bad_tab(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": None,
            "current_activity_id": None,
            "current_canvas_tab": "invalid",
            "methodology": None,
        },
    )
    assert response.status_code == 422

    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": None,
            "current_activity_id": None,
            "current_canvas_tab": "document",
            "methodology": None,
            "tenant_id": "override",
        },
    )
    assert response.status_code == 422
