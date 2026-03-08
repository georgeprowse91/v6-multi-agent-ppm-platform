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
from connector_hub_proxy import ConnectorHubClient  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def _wire_client(monkeypatch, transport: httpx.AsyncBaseTransport) -> None:
    def _client() -> ConnectorHubClient:
        return ConnectorHubClient(base_url="http://connector-hub:8080", transport=transport)

    monkeypatch.setattr(main, "_connector_hub_client", _client)


def test_types_reads_registry_file(client):
    response = client.get("/api/connector-gallery/types")

    assert response.status_code == 200
    payload = response.json()
    registry_path = (
        Path(__file__).resolve().parents[3] / "connectors" / "registry" / "connectors.json"
    )
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry_ids = {entry["id"] for entry in registry}
    response_ids = {entry["id"] for entry in payload}
    assert registry_ids == response_ids


def test_instances_list_proxies_and_forwards_headers(client, monkeypatch):
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["path"] = request.url.path
        return httpx.Response(200, json=[{"connector_id": "conn-1"}])

    transport = httpx.MockTransport(handler)
    _wire_client(monkeypatch, transport)
    _set_tenant(monkeypatch, "tenant-a")

    response = client.get("/api/connector-gallery/instances", headers={"X-Dev-User": "tester"})

    assert response.status_code == 200
    assert response.json() == [{"connector_id": "conn-1"}]
    assert captured["path"] == "/connectors"
    assert captured["headers"]["authorization"] == "Bearer dev-token"
    assert captured["headers"]["x-tenant-id"] == "tenant-a"
    assert captured["headers"]["x-dev-user"] == "tester"


def test_create_instance_maps_type_to_connector_request(client, monkeypatch):
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "connector_id": "conn-99",
                "name": "jira",
                "version": "1.2.3",
                "enabled": True,
                "health_status": "unknown",
                "last_checked": None,
                "metadata": {"connector_type_id": "jira", "instance_url": "https://jira"},
            },
        )

    transport = httpx.MockTransport(handler)
    _wire_client(monkeypatch, transport)
    _set_tenant(monkeypatch, "tenant-a")

    response = client.post(
        "/api/connector-gallery/instances",
        json={
            "connector_type_id": "jira",
            "version": "1.2.3",
            "enabled": True,
            "metadata": {"instance_url": "https://jira", "notes": "primary"},
        },
    )

    assert response.status_code == 200
    assert captured["json"] == {
        "name": "jira",
        "version": "1.2.3",
        "enabled": True,
        "metadata": {
            "connector_type_id": "jira",
            "instance_url": "https://jira",
            "notes": "primary",
        },
    }


def test_update_instance_enable_disable(client, monkeypatch):
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["json"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "connector_id": "conn-1",
                "name": "jira",
                "version": "1.2.3",
                "enabled": False,
                "health_status": "unknown",
                "last_checked": None,
                "metadata": {"connector_type_id": "jira"},
            },
        )

    transport = httpx.MockTransport(handler)
    _wire_client(monkeypatch, transport)
    _set_tenant(monkeypatch, "tenant-a")

    response = client.patch(
        "/api/connector-gallery/instances/conn-1",
        json={"enabled": False},
    )

    assert response.status_code == 200
    assert captured["path"] == "/connectors/conn-1"
    assert captured["json"] == {"enabled": False}


def test_health_proxy(client, monkeypatch):
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "connector_id": "conn-1",
                "name": "jira",
                "version": "1.2.3",
                "enabled": True,
                "health_status": "healthy",
                "last_checked": "2024-01-01T00:00:00Z",
                "metadata": {"connector_type_id": "jira"},
            },
        )

    transport = httpx.MockTransport(handler)
    _wire_client(monkeypatch, transport)
    _set_tenant(monkeypatch, "tenant-a")

    response = client.get("/api/connector-gallery/instances/conn-1/health")

    assert response.status_code == 200
    assert captured["path"] == "/connectors/conn-1/health"


def test_tenant_isolation(client, monkeypatch):
    async def handler_tenant_a(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-tenant-id"] == "tenant-a"
        return httpx.Response(200, json=[{"connector_id": "conn-a"}])

    transport_a = httpx.MockTransport(handler_tenant_a)
    _wire_client(monkeypatch, transport_a)
    _set_tenant(monkeypatch, "tenant-a")

    response = client.get("/api/connector-gallery/instances")
    assert response.status_code == 200
    assert response.json() == [{"connector_id": "conn-a"}]

    async def handler_tenant_b(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-tenant-id"] == "tenant-b"
        return httpx.Response(200, json=[{"connector_id": "conn-b"}])

    transport_b = httpx.MockTransport(handler_tenant_b)
    _wire_client(monkeypatch, transport_b)
    _set_tenant(monkeypatch, "tenant-b")

    response = client.get("/api/connector-gallery/instances")
    assert response.status_code == 200
    assert response.json() == [{"connector_id": "conn-b"}]
