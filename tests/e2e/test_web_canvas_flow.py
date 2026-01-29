from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

WEB_SRC = Path(__file__).resolve().parents[2] / "apps" / "web" / "src"
MODULE_PATH = WEB_SRC / "main.py"
spec = spec_from_file_location("web_main_e2e", MODULE_PATH)
assert spec and spec.loader
web_main = module_from_spec(spec)
sys.modules[spec.name] = web_main
spec.loader.exec_module(web_main)
from spreadsheet_store import SpreadsheetStore  # noqa: E402
from workspace_state_store import WorkspaceStateStore  # noqa: E402


@pytest.fixture
def web_client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", "tenant-e2e")
    web_main.spreadsheet_store = SpreadsheetStore(tmp_path / "spreadsheets.json")
    web_main.workspace_state_store = WorkspaceStateStore(tmp_path / "workspace_state.json")
    return TestClient(web_main.app)


def test_spreadsheet_canvas_flow(web_client):
    sheet_response = web_client.post(
        "/api/spreadsheets/demo-1/sheets",
        json={
            "name": "E2E Sheet",
            "columns": [
                {"name": "Task", "type": "text", "required": True},
                {"name": "Owner", "type": "text"},
            ],
        },
    )
    assert sheet_response.status_code == 200
    sheet = sheet_response.json()
    column_ids = {col["name"]: col["column_id"] for col in sheet["columns"]}

    row_response = web_client.post(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/rows",
        json={"values": {column_ids["Task"]: "E2E Task", column_ids["Owner"]: "Lee"}},
    )
    assert row_response.status_code == 200

    export_response = web_client.get(
        f"/api/spreadsheets/demo-1/sheets/{sheet['sheet_id']}/export.csv"
    )
    assert export_response.status_code == 200
    assert "E2E Task" in export_response.text


def test_assistant_suggestions_include_context(web_client):
    response = web_client.post(
        "/api/assistant/suggestions",
        json={
            "project_id": "demo-1",
            "activity_id": "agile-vision",
            "activity_name": "Product Vision Statement",
            "stage_id": "agile-discovery",
            "stage_name": "Discovery",
            "activity_status": "in_progress",
            "canvas_type": "document",
            "incomplete_prerequisites": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["context"]["activity_name"] == "Product Vision Statement"
    assert payload["suggestions"]


def test_template_apply_version(web_client):
    response = web_client.post(
        "/api/templates/agile-software-dev/apply",
        json={"project_name": "E2E Agile", "version": "1.0"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["template_version"] == "1.0"
