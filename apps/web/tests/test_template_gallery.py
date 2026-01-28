import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
from document_proxy import DocumentServiceClient  # noqa: E402
from spreadsheet_store import SpreadsheetStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    main.spreadsheet_store = SpreadsheetStore(tmp_path / "spreadsheets.json")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def _wire_document_client(monkeypatch, transport: httpx.AsyncBaseTransport) -> None:
    def _client() -> DocumentServiceClient:
        return DocumentServiceClient(base_url="http://document-service:8080", transport=transport)

    monkeypatch.setattr(main, "_document_client", _client)


def test_list_templates_filter_type_and_search(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get("/api/templates?type=document&q=charter")
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert all(item["type"] == "document" for item in payload)
    assert any(item["template_id"] == "project-charter" for item in payload)


def test_get_template(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get("/api/templates/status-report")
    assert response.status_code == 200
    payload = response.json()
    assert payload["template_id"] == "status-report"
    assert payload["payload"]["name_template"]


def test_instantiate_document_substitutes_placeholders(client, monkeypatch):
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "document_id": "doc-42",
                "name": captured["payload"]["name"],
                "classification": captured["payload"]["classification"],
                "retention_days": captured["payload"]["retention_days"],
                "created_at": "2024-01-01T00:00:00Z",
                "retention_until": "2024-03-31T00:00:00Z",
                "metadata": captured["payload"]["metadata"],
                "advisories": ["ok"],
            },
        )

    transport = httpx.MockTransport(handler)
    _wire_document_client(monkeypatch, transport)
    _set_tenant(monkeypatch, "tenant-a")

    response = client.post(
        "/api/templates/project-charter/instantiate",
        json={"project_id": "demo-1", "parameters": {"user": "Ava"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["created_type"] == "document"
    assert payload["document_id"] == "doc-42"

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert captured["payload"]["name"] == "demo-1 Project Charter"
    assert "tenant-a" in captured["payload"]["content"]
    assert today in captured["payload"]["content"]
    assert captured["payload"]["metadata"]["owner"] == "Ava"
    assert captured["payload"]["classification"] == "internal"


def test_instantiate_spreadsheet_creates_sheet_and_seed_rows(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/templates/risk-register/instantiate",
        json={"project_id": "demo-1", "parameters": {"user": "Pat"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["created_type"] == "spreadsheet"

    detail_response = client.get(
        f"/api/spreadsheets/demo-1/sheets/{payload['sheet_id']}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["rows"]
    columns = {col["name"]: col["column_id"] for col in detail["sheet"]["columns"]}
    row = detail["rows"][0]["values"]
    assert row[columns["Risk"]] == "Supplier delay"
    assert row[columns["Owner"]] == "Pat"


def test_tenant_isolation_instantiation(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/templates/action-log/instantiate",
        json={"project_id": "demo-1", "parameters": {"user": "Pat"}},
    )
    assert response.status_code == 200

    _set_tenant(monkeypatch, "tenant-b")
    list_response = client.get("/api/spreadsheets/demo-1/sheets")
    assert list_response.status_code == 200
    assert list_response.json() == []
