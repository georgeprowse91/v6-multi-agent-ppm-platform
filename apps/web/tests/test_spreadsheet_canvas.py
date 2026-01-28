import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
from spreadsheet_store import SpreadsheetStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    main.spreadsheet_store = SpreadsheetStore(tmp_path / "spreadsheets.json")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def _create_sheet(client: TestClient, project_id: str) -> dict:
    response = client.post(
        f"/api/spreadsheets/{project_id}/sheets",
        json={
            "name": "Backlog",
            "columns": [
                {"name": "Task", "type": "text", "required": True},
                {"name": "Estimate", "type": "number"},
            ],
        },
    )
    assert response.status_code == 200
    return response.json()


def test_create_sheet_and_list(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    sheet = _create_sheet(client, "demo-1")

    list_response = client.get("/api/spreadsheets/demo-1/sheets")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["sheet_id"] == sheet["sheet_id"]


def test_add_row_and_type_validation(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    sheet_response = client.post(
        "/api/spreadsheets/demo-1/sheets",
        json={
            "name": "Typed",
            "columns": [
                {"name": "Task", "type": "text", "required": True},
                {"name": "Estimate", "type": "number", "required": True},
                {"name": "Due", "type": "date"},
                {"name": "Done", "type": "bool"},
            ],
        },
    )
    sheet = sheet_response.json()
    column_ids = {col["name"]: col["column_id"] for col in sheet["columns"]}

    row_response = client.post(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/rows",
        json={
            "values": {
                column_ids["Task"]: "Ship",
                column_ids["Estimate"]: "3.5",
                column_ids["Due"]: "2024-06-01",
                column_ids["Done"]: "true",
            }
        },
    )
    assert row_response.status_code == 200
    row_payload = row_response.json()
    assert row_payload["values"][column_ids["Estimate"]] == 3.5
    assert row_payload["values"][column_ids["Done"]] is True

    bad_response = client.post(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/rows",
        json={
            "values": {
                column_ids["Task"]: "Bad",
                column_ids["Estimate"]: "nope",
            }
        },
    )
    assert bad_response.status_code == 422


def test_required_column_enforced(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    sheet = _create_sheet(client, "demo-1")
    column_id = sheet["columns"][0]["column_id"]

    response = client.post(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/rows",
        json={"values": {}},
    )
    assert response.status_code == 422

    response = client.post(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/rows",
        json={"values": {column_id: ""}},
    )
    assert response.status_code == 422


def test_update_row_partial(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    sheet = _create_sheet(client, "demo-1")
    task_id = sheet["columns"][0]["column_id"]
    estimate_id = sheet["columns"][1]["column_id"]

    row_response = client.post(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/rows",
        json={"values": {task_id: "Initial", estimate_id: "2"}},
    )
    row = row_response.json()

    update_response = client.patch(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/rows/{row['row_id']}",
        json={"values": {estimate_id: "4"}},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["values"][task_id] == "Initial"
    assert updated["values"][estimate_id] == 4.0


def test_export_csv(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    sheet = _create_sheet(client, "demo-1")
    task_id = sheet["columns"][0]["column_id"]
    estimate_id = sheet["columns"][1]["column_id"]

    client.post(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/rows",
        json={"values": {task_id: "Plan", estimate_id: "1"}},
    )

    response = client.get(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/export.csv"
    )
    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert lines[0].strip() == "Task,Estimate"
    assert "Plan" in lines[1]


def test_import_csv_success_and_failure(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    sheet = _create_sheet(client, "demo-1")

    csv_payload = "Task,Estimate\nBuild,5\n"
    response = client.post(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/import.csv",
        data=csv_payload,
        headers={"Content-Type": "text/csv"},
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 1

    bad_csv = "Task,Estimate\nBad,not-a-number\n"
    response = client.post(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/import.csv",
        data=bad_csv,
        headers={"Content-Type": "text/csv"},
    )
    assert response.status_code == 422


def test_tenant_isolation(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    _create_sheet(client, "demo-1")

    _set_tenant(monkeypatch, "tenant-b")
    response = client.get("/api/spreadsheets/demo-1/sheets")
    assert response.status_code == 200
    assert response.json() == []
