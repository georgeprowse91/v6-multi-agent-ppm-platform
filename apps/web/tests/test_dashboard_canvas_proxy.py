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
from analytics_proxy import AnalyticsServiceClient  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def _wire_client(monkeypatch, transport: httpx.AsyncBaseTransport) -> None:
    def _client() -> AnalyticsServiceClient:
        return AnalyticsServiceClient(
            base_url="http://analytics-service:8080", transport=transport
        )

    monkeypatch.setattr(main, "_analytics_client", _client)


def test_health_proxy_forwards_headers(client, monkeypatch):
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["path"] = request.url.path
        return httpx.Response(200, json={"health_status": "Healthy"})

    transport = httpx.MockTransport(handler)
    _wire_client(monkeypatch, transport)
    _set_tenant(monkeypatch, "tenant-a")

    response = client.get(
        "/api/dashboard/demo-1/health", headers={"X-Dev-User": "tester"}
    )

    assert response.status_code == 200
    assert captured["path"] == "/api/projects/demo-1/health"
    assert captured["headers"]["authorization"] == "Bearer dev-token"
    assert captured["headers"]["x-tenant-id"] == "tenant-a"
    assert captured["headers"]["x-dev-user"] == "tester"


def test_trends_proxy_forwards_headers(client, monkeypatch):
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["path"] = request.url.path
        return httpx.Response(200, json={"points": []})

    transport = httpx.MockTransport(handler)
    _wire_client(monkeypatch, transport)
    _set_tenant(monkeypatch, "tenant-a")

    response = client.get("/api/dashboard/demo-1/trends")

    assert response.status_code == 200
    assert captured["path"] == "/api/projects/demo-1/health/trends"
    assert captured["headers"]["authorization"] == "Bearer dev-token"
    assert captured["headers"]["x-tenant-id"] == "tenant-a"


def test_whatif_proxy_forwards_headers_and_body(client, monkeypatch):
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "project_id": "demo-1",
                "scenario_id": "scenario-1",
                "status": "queued",
                "message": "Queued",
            },
        )

    transport = httpx.MockTransport(handler)
    _wire_client(monkeypatch, transport)
    _set_tenant(monkeypatch, "tenant-a")

    response = client.post(
        "/api/dashboard/demo-1/what-if",
        json={"scenario": "Delay vendor", "adjustments": {"risk_score": 0.2}},
        headers={"X-Dev-User": "tester"},
    )

    assert response.status_code == 200
    assert captured["path"] == "/api/projects/demo-1/health/what-if"
    assert captured["headers"]["authorization"] == "Bearer dev-token"
    assert captured["headers"]["x-tenant-id"] == "tenant-a"
    assert captured["headers"]["x-dev-user"] == "tester"
    assert captured["body"] == {
        "scenario": "Delay vendor",
        "adjustments": {"risk_score": 0.2},
    }


def test_proxy_propagates_error_status_and_payload(client, monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"detail": "upstream error"})

    transport = httpx.MockTransport(handler)
    _wire_client(monkeypatch, transport)
    _set_tenant(monkeypatch, "tenant-a")

    response = client.get("/api/dashboard/demo-1/health")

    assert response.status_code == 502
    assert response.json() == {"detail": "upstream error"}
