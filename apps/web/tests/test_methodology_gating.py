import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
from gating import evaluate_activity_access, next_required_activity, stage_progress  # noqa: E402
from methodologies import get_methodology_map  # noqa: E402
from workspace_state import build_default_state  # noqa: E402
from workspace_state_store import WorkspaceStateStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    main.workspace_state_store = WorkspaceStateStore(tmp_path / "workspace_state.json")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def test_monitoring_never_blocked():
    methodology_map = get_methodology_map("agile")
    state = build_default_state("tenant-a", "demo-1")
    access = evaluate_activity_access(methodology_map, state, "monitoring-health")
    assert access["allowed"] is True
    assert access["missing_prereqs"] == []


def test_prereq_blocks_activity_until_complete():
    methodology_map = get_methodology_map("agile")
    state = build_default_state("tenant-a", "demo-1")
    access = evaluate_activity_access(methodology_map, state, "agile-release-plan")
    assert access["allowed"] is False
    assert access["missing_prereqs"] == ["agile-backlog"]

    state.activity_completion["agile-backlog"] = True
    access = evaluate_activity_access(methodology_map, state, "agile-release-plan")
    assert access["allowed"] is True


def test_next_required_activity_returns_prereq():
    methodology_map = get_methodology_map("agile")
    state = build_default_state("tenant-a", "demo-1")
    state.current_activity_id = "agile-release-plan"
    assert next_required_activity(methodology_map, state) == "agile-backlog"


def test_stage_progress_calculation():
    methodology_map = get_methodology_map("agile")
    state = build_default_state("tenant-a", "demo-1")
    state.activity_completion["agile-backlog"] = True
    progress = stage_progress(methodology_map, state, "agile-planning")
    assert progress["complete_count"] == 1
    assert progress["total_count"] == 2
    assert progress["percent"] == 50.0


def test_api_returns_gating_metadata(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": "agile-planning",
            "current_activity_id": "agile-release-plan",
            "current_canvas_tab": "timeline",
            "methodology": "agile",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "available_methodologies" in payload
    assert payload["gating"]["current_activity_access"]["allowed"] is False
    assert payload["gating"]["current_activity_access"]["missing_prereqs"] == [
        "agile-backlog"
    ]
    assert payload["gating"]["next_required_activity_id"] == "agile-backlog"


def test_tenant_isolation_for_completion_and_gating(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/activity-completion",
        json={"activity_id": "agile-vision", "completed": True},
    )
    assert response.status_code == 200
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": "agile-discovery",
            "current_activity_id": "agile-stakeholder-map",
            "current_canvas_tab": "tree",
            "methodology": "agile",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["gating"]["current_activity_access"]["allowed"] is True

    _set_tenant(monkeypatch, "tenant-b")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": "agile-discovery",
            "current_activity_id": "agile-stakeholder-map",
            "current_canvas_tab": "tree",
            "methodology": "agile",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["gating"]["current_activity_access"]["allowed"] is False
    assert payload["gating"]["current_activity_access"]["missing_prereqs"] == [
        "agile-vision"
    ]
