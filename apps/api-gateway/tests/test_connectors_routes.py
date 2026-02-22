from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from api.routes import connectors
from fastapi import HTTPException
from pydantic import ValidationError

from integrations.connectors.mcp_client.errors import MCPAuthenticationError, MCPResponseError


class _DummyConfigStore:
    def __init__(self, config):
        self._config = config

    def get(self, _connector_id: str):
        return self._config


@pytest.mark.anyio
async def test_list_mcp_server_tools_success_shape(monkeypatch):
    definition = SimpleNamespace(connector_id="jira", mcp_server_id="jira-server")
    config = SimpleNamespace(mcp_server_url="https://mcp.example", mcp_server_id="")

    async def _list_tools(self):
        return [
            SimpleNamespace(name="search", description="Search", input_schema={"type": "object"})
        ]

    monkeypatch.setattr(connectors, "_get_mcp_definition_by_system", lambda _system: definition)
    monkeypatch.setattr(connectors, "get_config_store", lambda _request: _DummyConfigStore(config))
    monkeypatch.setattr(connectors.MCPClient, "list_tools", _list_tools)
    monkeypatch.setattr(connectors, "http_request", object(), raising=False)

    response = await connectors.list_mcp_server_tools("jira")

    assert response.system == "jira"
    assert response.server_url == "https://mcp.example"
    assert response.tools[0].name == "search"


@pytest.mark.anyio
async def test_list_mcp_server_tools_maps_auth_error(monkeypatch):
    definition = SimpleNamespace(connector_id="jira", mcp_server_id="jira-server")
    config = SimpleNamespace(mcp_server_url="https://mcp.example", mcp_server_id="")

    async def _raise_auth(self):
        raise MCPAuthenticationError("bad credentials")

    monkeypatch.setattr(connectors, "_get_mcp_definition_by_system", lambda _system: definition)
    monkeypatch.setattr(connectors, "get_config_store", lambda _request: _DummyConfigStore(config))
    monkeypatch.setattr(connectors.MCPClient, "list_tools", _raise_auth)
    monkeypatch.setattr(connectors, "http_request", object(), raising=False)

    with pytest.raises(HTTPException) as exc_info:
        await connectors.list_mcp_server_tools("jira")

    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_list_mcp_server_tools_maps_upstream_rate_limit_error(monkeypatch):
    definition = SimpleNamespace(connector_id="jira", mcp_server_id="jira-server")
    config = SimpleNamespace(mcp_server_url="https://mcp.example", mcp_server_id="")

    async def _raise_rate_limit(self):
        raise MCPResponseError("429 upstream rate limit")

    monkeypatch.setattr(connectors, "_get_mcp_definition_by_system", lambda _system: definition)
    monkeypatch.setattr(connectors, "get_config_store", lambda _request: _DummyConfigStore(config))
    monkeypatch.setattr(connectors.MCPClient, "list_tools", _raise_rate_limit)
    monkeypatch.setattr(connectors, "http_request", object(), raising=False)

    with pytest.raises(HTTPException) as exc_info:
        await connectors.list_mcp_server_tools("jira")

    assert exc_info.value.status_code == 502


def test_connector_config_request_validates_and_normalizes_tooling_fields():
    request = connectors.ConnectorConfigRequest(
        mcp_scope="read write",
        mcp_tools=["create_ticket"],
    )

    assert request.mcp_scopes == ["read", "write"]
    assert request.mcp_tool_map == {"create_ticket": "create_ticket"}
    assert request.tool_map == {}


def test_connector_config_request_rejects_invalid_tool_map_shape():
    with pytest.raises(ValidationError):
        connectors.ConnectorConfigRequest(mcp_tool_map={"tool": 123})


def test_sanitize_headers_removes_secrets_only():
    sanitized = connectors._sanitize_headers(
        {
            "content-type": "application/json",
            "x-webhook-secret": "top-secret",
            "x-webhook-signature": "sha256=abc",
            "x-request-id": "req-1",
        }
    )

    assert "x-webhook-secret" not in sanitized
    assert "x-webhook-signature" not in sanitized
    assert sanitized["x-request-id"] == "req-1"


@pytest.mark.anyio
async def test_test_connection_records_failure_on_timeout(monkeypatch):
    definition = SimpleNamespace(
        connector_id="jira",
        name="Jira",
        category=connectors.ConnectorCategory.PPM,
        status=connectors.ConnectorStatus.AVAILABLE,
    )

    class _Store:
        def get(self, _connector_id: str):
            return None

    class _Breaker:
        def __init__(self):
            self.failures = 0

        def allow_request(self, _key: str) -> bool:
            return True

        def record_failure(self, _key: str) -> None:
            self.failures += 1

        def record_success(self, _key: str) -> None:
            raise AssertionError("should not be called")

    def _handler(_config):
        raise TimeoutError("upstream timeout")

    breaker = _Breaker()
    monkeypatch.setattr(connectors, "get_connector_definition", lambda _id: definition)
    monkeypatch.setattr(connectors, "get_config_store", lambda _request: _Store())
    monkeypatch.setattr(
        connectors, "get_test_connection_handler", lambda *_args, **_kwargs: ("function", _handler)
    )
    monkeypatch.setattr(connectors, "get_circuit_breaker", lambda _request: breaker)
    monkeypatch.setattr(connectors, "http_request", object(), raising=False)

    request = connectors.TestConnectionRequest(
        instance_url="https://jira.example", project_key="PPM"
    )
    with pytest.raises(HTTPException) as exc_info:
        await connectors.test_connection("jira", request)

    assert exc_info.value.status_code == 502
    assert breaker.failures == 1


@pytest.mark.anyio
async def test_test_connection_success_response_shape(monkeypatch):
    definition = SimpleNamespace(
        connector_id="jira",
        name="Jira",
        category=connectors.ConnectorCategory.PPM,
        status=connectors.ConnectorStatus.AVAILABLE,
    )

    class _Store:
        def __init__(self):
            self.saved = None

        def get(self, _connector_id: str):
            return None

        def save(self, _config):
            self.saved = _config

    class _Breaker:
        def allow_request(self, _key: str) -> bool:
            return True

        def record_failure(self, _key: str) -> None:
            raise AssertionError("should not be called")

        def record_success(self, _key: str) -> None:
            return None

    class _Result:
        status = connectors.ConnectionStatus.CONNECTED
        message = "ok"
        details = {"latency_ms": 10}
        tested_at = datetime.now(timezone.utc)

    store = _Store()
    monkeypatch.setattr(connectors, "get_connector_definition", lambda _id: definition)
    monkeypatch.setattr(connectors, "get_config_store", lambda _request: store)
    monkeypatch.setattr(
        connectors,
        "get_test_connection_handler",
        lambda *_args, **_kwargs: ("function", lambda _cfg: _Result()),
    )
    monkeypatch.setattr(connectors, "get_circuit_breaker", lambda _request: _Breaker())
    monkeypatch.setattr(connectors, "http_request", object(), raising=False)

    request = connectors.TestConnectionRequest(
        instance_url="https://jira.example", project_key="PPM"
    )
    response = await connectors.test_connection("jira", request)

    assert response.status == "connected"
    assert response.message == "ok"
    assert response.details == {"latency_ms": 10}
