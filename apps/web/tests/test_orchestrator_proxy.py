import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
from orchestrator_proxy import OrchestratorProxyClient  # noqa: E402
from workspace_state_store import WorkspaceStateStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", "tenant-a")
    main.workspace_state_store = WorkspaceStateStore(tmp_path / "workspace_state.json")
    return TestClient(main.app)


def _mock_orchestrator_client(monkeypatch, handler):
    transport = httpx.MockTransport(handler)

    def _factory():
        return OrchestratorProxyClient(
            base_url="http://api-gateway:8000", timeout=1.0, transport=transport
        )

    monkeypatch.setattr(main, "_orchestrator_client", _factory)


def test_send_forwards_headers_and_query(client, monkeypatch):
    captured = {}

    def handler(request):
        captured["headers"] = dict(request.headers)
        captured["json"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"success": True, "data": {"message": "ok"}})

    _mock_orchestrator_client(monkeypatch, handler)
    response = client.post(
        "/api/assistant/send",
        headers={"X-Dev-User": "alice"},
        json={"project_id": "demo-1", "message": "Hello assistant"},
    )
    assert response.status_code == 200
    assert captured["json"]["query"] == "Hello assistant"
    context = captured["json"]["context"]
    assert context["tenant_id"] == "tenant-a"
    assert captured["headers"]["authorization"] == "Bearer dev-token"
    assert captured["headers"]["x-tenant-id"] == "tenant-a"
    assert captured["headers"]["x-dev-user"] == "alice"


def test_send_generates_correlation_id(client, monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"success": True, "data": {"message": "ok"}})

    _mock_orchestrator_client(monkeypatch, handler)
    response = client.post(
        "/api/assistant/send",
        json={"project_id": "demo-1", "message": "Hello assistant"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["correlation_id"].startswith("corr-")


def test_send_includes_workspace_context_if_available(client, monkeypatch):
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": "stage-1",
            "current_activity_id": "activity-1",
            "current_canvas_tab": "document",
            "methodology": "hybrid",
            "open_ref": {"document_id": "doc-123"},
        },
    )
    assert response.status_code == 200
    captured = {}

    def handler(request):
        captured["json"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"success": True, "data": {"message": "ok"}})

    _mock_orchestrator_client(monkeypatch, handler)
    response = client.post(
        "/api/assistant/send",
        json={"project_id": "demo-1", "message": "Hello assistant"},
    )
    assert response.status_code == 200
    context = captured["json"]["context"]
    assert context["methodology"] == "hybrid"
    assert context["current_stage_id"] == "stage-1"
    assert context["current_activity_id"] == "activity-1"
    assert context["current_canvas_tab"] == "document"
    assert context["open_ref"] == {"document_id": "doc-123"}


def test_send_propagates_upstream_error(client, monkeypatch):
    def handler(request):
        return httpx.Response(502, json={"detail": "bad gateway"})

    _mock_orchestrator_client(monkeypatch, handler)
    response = client.post(
        "/api/assistant/send",
        json={"project_id": "demo-1", "message": "Hello assistant"},
    )
    assert response.status_code == 502
    payload = response.json()
    assert payload["detail"] == "bad gateway"
    assert payload["correlation_id"].startswith("corr-")


def test_send_timeout_returns_504(client, monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("timeout")

    _mock_orchestrator_client(monkeypatch, handler)
    response = client.post(
        "/api/assistant/send",
        json={"project_id": "demo-1", "message": "Hello assistant"},
    )
    assert response.status_code == 504
    payload = response.json()
    assert payload["detail"] == "upstream timeout"
    assert payload["correlation_id"].startswith("corr-")
