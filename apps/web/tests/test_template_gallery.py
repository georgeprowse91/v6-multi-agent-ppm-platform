import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
MODULE_PATH = SRC_DIR / "main.py"
spec = spec_from_file_location("web_main", MODULE_PATH)
assert spec and spec.loader
main = module_from_spec(spec)
sys.modules[spec.name] = main
spec.loader.exec_module(main)
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
    response = client.get("/api/templates?gallery=true&artefact=charter&q=charter")
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert all(item["artefact_type"] == "charter" for item in payload)
    assert any(item["template_id"] == "project-charter.universal.v1" for item in payload)


def test_get_template(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get("/api/templates/status-report?gallery=true")
    assert response.status_code == 200
    payload = response.json()
    assert payload["template_id"] == "status-report.universal.v1"
    assert payload["canonical_template_id"] == "status-report.universal.v1"
    assert payload["legacy_ids"]


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

    detail_response = client.get(f"/api/spreadsheets/demo-1/sheets/{payload['sheet_id']}")
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


def test_apply_template_with_version(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/templates/agile-software-dev/apply",
        json={"project_name": "Agile Demo", "version": "1.0"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["template_version"] == "1.0"
    assert payload["template"]["version"] == "1.0"


@pytest.mark.parametrize(
    ("template_id", "expected_methodology_id"),
    [
        ("agile-software-dev", "adaptive"),
        ("waterfall-infrastructure", "predictive"),
        ("hybrid-transformation", "hybrid"),
    ],
)
def test_apply_template_returns_yaml_methodology_map(
    client, monkeypatch, template_id: str, expected_methodology_id: str
):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        f"/api/templates/{template_id}/apply",
        json={"project_name": f"{template_id}-project", "version": "1.0"},
    )
    assert response.status_code == 200
    payload = response.json()

    methodology = payload["template"]["methodology"]
    assert methodology["id"] == expected_methodology_id
    assert methodology["navigation_nodes"]

    stage_activities = [
        activity
        for stage in methodology["stages"]
        for activity in stage.get("activities", [])
    ]
    assert stage_activities

    assert payload["project"]["methodology"]["id"] == expected_methodology_id
