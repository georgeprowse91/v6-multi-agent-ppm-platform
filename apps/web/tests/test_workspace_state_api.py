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
            "methodology": "adaptive",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["current_canvas_tab"] == "timeline"
    assert payload["methodology"] == "adaptive"

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


def test_get_workspace_supports_methodology_query(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get('/api/workspace/demo-1?methodology=predictive')
    assert response.status_code == 200
    payload = response.json()
    assert payload['methodology'] == 'predictive'
    assert payload['methodology_map_summary']['id'] == 'predictive'


def test_get_workspace_rejects_unknown_methodology_query(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get('/api/workspace/demo-1?methodology=unknown')
    assert response.status_code == 422


def test_runtime_resolution_endpoints_and_workspace_enrichment(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "current_activity_id": "0.5.1-sprint-iteration-planning",
            "current_canvas_tab": "document",
            "methodology": "adaptive",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "view" in payload["runtime_actions_available"]
    assert payload["runtime_default_view_contract"]["canvas"]["renderer_component"]

    actions = client.get(
        "/api/methodology/runtime/actions",
        params={
            "methodology_id": "adaptive",
            "stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "activity_id": "0.5.1-sprint-iteration-planning",
        },
    )
    assert actions.status_code == 200
    assert "generate" in actions.json()["actions"]

    resolved = client.get(
        "/api/methodology/runtime/resolve",
        params={
            "methodology_id": "adaptive",
            "stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "activity_id": "0.5.1-sprint-iteration-planning",
            "event": "view",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolution_contract"]["assistant"]["response_contract"]["output_format"]
