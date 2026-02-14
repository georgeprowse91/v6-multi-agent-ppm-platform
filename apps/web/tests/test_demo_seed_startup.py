import importlib
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
import types

if "email_validator" not in sys.modules:
    module = types.ModuleType("email_validator")
    module.EmailNotValidError = ValueError
    module.validate_email = lambda value, **kwargs: types.SimpleNamespace(email=value)
    sys.modules["email_validator"] = module

if "event_bus" not in sys.modules:
    module = types.ModuleType("event_bus")
    module.EventHandler = object
    module.EventRecord = dict
    class _Bus:
        async def publish(self, *args, **kwargs):
            return None
    module.ServiceBusEventBus = _Bus
    module.get_event_bus = lambda *args, **kwargs: _Bus()
    sys.modules["event_bus"] = module

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", "demo-tenant")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEMO_MODE", "true")

    import main  # noqa: E402

    main = importlib.reload(main)
    from workspace_state_store import WorkspaceStateStore  # noqa: E402
    from spreadsheet_store import SpreadsheetStore  # noqa: E402
    from timeline_store import TimelineStore  # noqa: E402
    from tree_store import TreeStore  # noqa: E402

    main.workspace_state_store = WorkspaceStateStore(tmp_path / "workspace_state.json")
    main.spreadsheet_store = SpreadsheetStore(tmp_path / "spreadsheets.json")
    main.timeline_store = TimelineStore(tmp_path / "timelines.json")
    main.tree_store = TreeStore(tmp_path / "trees.json")
    main.KNOWLEDGE_DB_PATH = tmp_path / "knowledge.db"

    with TestClient(main.app) as test_client:
        yield test_client


def test_demo_startup_seeds_workspace_projects(client):
    for project_id, methodology in [
        ("demo-predictive", "predictive"),
        ("demo-adaptive", "adaptive"),
        ("demo-hybrid", "hybrid"),
    ]:
        response = client.get(f"/api/workspace/{project_id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["tenant_id"] == "demo-tenant"
        assert payload["methodology"] == methodology
        assert payload["methodology_map_summary"]["stages"]
        assert payload["methodology_map_summary"]["monitoring"]
        assert payload["activity_completion"]
        assert payload["methodology_map_summary"]["stages"][0]["activities"]


def test_demo_startup_seeds_all_methodologies_with_deep_stage_activity_payload(client):
    for project_id, methodology in [
        ("demo-predictive", "predictive"),
        ("demo-adaptive", "adaptive"),
        ("demo-hybrid", "hybrid"),
    ]:
        response = client.get(f"/api/workspace/{project_id}?methodology={methodology}")
        assert response.status_code == 200
        payload = response.json()
        stages = payload["methodology_map_summary"]["stages"]
        assert stages
        assert all(stage["activities"] for stage in stages)
        assert payload["runtime_actions_available"]


def test_demo_startup_seeds_entities_and_artifacts(client):
    projects_path = Path(__file__).resolve().parents[1] / "data" / "projects.json"
    projects = json.loads(projects_path.read_text(encoding="utf-8"))["projects"]
    project_ids = {project["id"] for project in projects}
    assert {"demo-predictive", "demo-adaptive", "demo-hybrid"}.issubset(project_ids)

    tree = client.get("/api/tree/demo-predictive")
    assert tree.status_code == 200
    node_types = {node["type"] for node in tree.json()["nodes"]}
    assert {"document", "sheet", "milestone", "dashboard"}.issubset(node_types)


def test_workspace_response_is_yaml_backed_in_demo(client):
    response = client.get("/api/workspace/demo-predictive")
    payload = response.json()
    stage_ids = [stage["id"] for stage in payload["methodology_map_summary"]["stages"]]
    assert "0.4-planning" in stage_ids
    first_stage_activity_ids = [
        activity["id"]
        for activity in payload["methodology_map_summary"]["stages"][0]["activities"]
    ]
    assert any(activity_id.startswith("0.1") for activity_id in first_stage_activity_ids)
