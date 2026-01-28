import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
from timeline_store import TimelineStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    main.timeline_store = TimelineStore(tmp_path / "timelines.json")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def test_create_list_update_delete_milestone(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    create_response = client.post(
        "/api/timeline/demo-1/milestones",
        json={
            "title": "Kickoff",
            "date": "2024-06-01",
            "status": "planned",
            "owner": "Jordan",
            "notes": "Align stakeholders",
        },
    )
    assert create_response.status_code == 200
    milestone = create_response.json()
    milestone_id = milestone["milestone_id"]

    list_response = client.get("/api/timeline/demo-1")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["project_id"] == "demo-1"
    assert len(payload["milestones"]) == 1

    update_response = client.patch(
        f"/api/timeline/demo-1/milestones/{milestone_id}",
        json={"status": "complete", "title": "Kickoff complete"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["status"] == "complete"
    assert updated["title"] == "Kickoff complete"

    delete_response = client.delete(
        f"/api/timeline/demo-1/milestones/{milestone_id}")
    assert delete_response.status_code == 200

    list_response = client.get("/api/timeline/demo-1")
    payload = list_response.json()
    assert payload["milestones"] == []


def test_validation_rejects_bad_date(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/timeline/demo-1/milestones",
        json={
            "title": "Bad date",
            "date": "2024-13-40",
            "status": "planned",
        },
    )
    assert response.status_code == 422


def test_validation_rejects_missing_title(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/timeline/demo-1/milestones",
        json={
            "date": "2024-06-01",
            "status": "planned",
        },
    )
    assert response.status_code == 422


def test_tenant_isolation(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    create_response = client.post(
        "/api/timeline/demo-1/milestones",
        json={
            "title": "Tenant A milestone",
            "date": "2024-06-10",
            "status": "planned",
        },
    )
    assert create_response.status_code == 200

    _set_tenant(monkeypatch, "tenant-b")
    list_response = client.get("/api/timeline/demo-1")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["tenant_id"] == "tenant-b"
    assert payload["milestones"] == []


def test_export_contains_milestones(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    client.post(
        "/api/timeline/demo-1/milestones",
        json={
            "title": "Kickoff",
            "date": "2024-06-01",
            "status": "planned",
        },
    )
    client.post(
        "/api/timeline/demo-1/milestones",
        json={
            "title": "Launch",
            "date": "2024-07-01",
            "status": "at_risk",
        },
    )

    export_response = client.get("/api/timeline/demo-1/export")
    assert export_response.status_code == 200
    payload = export_response.json()
    assert payload["project_id"] == "demo-1"
    assert payload["tenant_id"] == "tenant-a"
    assert len(payload["milestones"]) == 2
    assert payload["milestones"][0]["title"] == "Kickoff"
