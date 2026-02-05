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
    monkeypatch.setenv("DEMO_MODE", "true")
    main._demo_wbs_state = {}
    main._demo_schedule_state = {}
    return TestClient(main.app)


def test_get_wbs_returns_items(client, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", "tenant-a")
    response = client.get("/api/wbs/demo-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "demo-1"
    assert payload["items"]


def test_patch_wbs_updates_order(client, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", "tenant-a")
    initial = client.get("/api/wbs/demo-1").json()
    item_id = initial["items"][0]["id"]
    response = client.patch(
        "/api/wbs/demo-1",
        json={"item_id": item_id, "parent_id": None, "order": 42},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["order"] == 42
    refreshed = client.get("/api/wbs/demo-1").json()
    stored = next(item for item in refreshed["items"] if item["id"] == item_id)
    assert stored["order"] == 42


def test_patch_wbs_rejects_updates_when_not_in_demo_mode(client, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", "tenant-a")
    monkeypatch.setenv("DEMO_MODE", "false")
    initial = client.get("/api/wbs/demo-1").json()
    item_id = initial["items"][0]["id"]

    response = client.patch(
        "/api/wbs/demo-1",
        json={"item_id": item_id, "parent_id": None, "order": 3},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "WBS updates are available in demo mode."


def test_get_schedule_returns_tasks(client, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", "tenant-a")
    response = client.get("/api/schedule/demo-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "demo-1"
    assert payload["tasks"]
    assert payload["tasks"][1]["dependencies"] == ["demo-1-kickoff"]
