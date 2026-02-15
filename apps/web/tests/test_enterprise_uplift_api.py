import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
MODULE_PATH = SRC_DIR / "main.py"
spec = spec_from_file_location("web_main_enterprise", MODULE_PATH)
assert spec and spec.loader
main = module_from_spec(spec)
sys.modules[spec.name] = main
spec.loader.exec_module(main)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    return TestClient(main.app)


def test_scenario_results_deterministic(client):
    payload = {"id": "dem-test-1", "title": "Deterministic", "value": 8, "effort": 3, "risk": 2, "cost": 100}
    client.post("/v1/api/portfolio/demo-portfolio/demand", json=payload)
    first = client.post("/v1/api/portfolio/demo-portfolio/scenarios/run", json={"name": "Det", "limit": 5}).json()
    second = client.post("/v1/api/portfolio/demo-portfolio/scenarios/run", json={"name": "Det", "limit": 5}).json()
    assert first["value_score"] == second["value_score"]
    assert first["budget"] == second["budget"]


def test_mention_creates_notification_and_mark_read(client):
    comment = client.post(
        "/v1/api/comments",
        json={"workspace_id": "demo-project", "artifact_id": "a1", "text": "Please review @demo-user"},
    )
    assert comment.status_code == 200
    notifications = client.get("/v1/api/notifications").json()["notifications"]
    mention = next(item for item in notifications if "Mentioned in comment" in str(item.get("message", "")))
    mark = client.post(f"/v1/api/notifications/{mention['id']}/read")
    assert mark.status_code == 200
    assert mark.json()["read"] is True


def test_budget_versioning_and_diff(client):
    first = client.post("/v1/api/finance/budgets", json={"workspace_id": "demo-program", "amounts": {"capex": 100}}).json()
    second = client.post("/v1/api/finance/budgets", json={"workspace_id": "demo-program", "amounts": {"capex": 130}}).json()
    assert first["version"] + 1 == second["version"]
    assert second["diff"]["capex"] == 30


def test_board_config_persistence(client):
    payload = {"workspace_id": "demo-program", "entity": "demand", "view": "kanban", "columns": ["title", "status"]}
    client.post("/v1/api/boards/config", json=payload)
    loaded = client.get("/v1/api/boards/config?workspace_id=demo-program&entity=demand").json()
    assert loaded["view"] == "kanban"


def test_sync_diff_and_conflict_resolution(client):
    diff = client.post(
        "/v1/api/sync/diff",
        json={"source": [{"id": "x1", "name": "incoming"}], "target": [{"id": "x1", "name": "current"}]},
    ).json()
    assert diff["conflicts"]
    conflict_id = diff["conflicts"][0]["id"]
    resolved = client.post(f"/v1/api/sync/conflicts/{conflict_id}/resolve", json={"decision": "incoming"}).json()
    assert resolved["status"] == "resolved"
