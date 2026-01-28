import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
from methodologies import METHODOLOGY_MAPS  # noqa: E402
from workspace_state_store import WorkspaceStateStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    main.workspace_state_store = WorkspaceStateStore(tmp_path / "workspace_state.json")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def test_workspace_get_includes_selected_activity_prompts(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": "agile-discovery",
            "current_activity_id": "agile-vision",
            "current_canvas_tab": "document",
            "methodology": "agile",
        },
    )
    assert response.status_code == 200

    response = client.get("/api/workspace/demo-1")
    assert response.status_code == 200
    payload = response.json()
    selected_activity = payload["selected_activity"]
    assert selected_activity["id"] == "agile-vision"
    assert 3 <= len(selected_activity["assistant_prompts"]) <= 6


def test_methodologies_define_prompt_counts():
    for methodology in METHODOLOGY_MAPS.values():
        first_stage = methodology["stages"][0]
        first_activity = first_stage["activities"][0]
        assert 3 <= len(first_activity["assistant_prompts"]) <= 6


def test_monitoring_activity_includes_prompts(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": None,
            "current_activity_id": "monitoring-risks",
            "current_canvas_tab": "document",
            "methodology": "hybrid",
        },
    )
    assert response.status_code == 200

    response = client.get("/api/workspace/demo-1")
    assert response.status_code == 200
    payload = response.json()
    selected_activity = payload["selected_activity"]
    assert selected_activity["id"] == "monitoring-risks"
    assert 3 <= len(selected_activity["assistant_prompts"]) <= 6
