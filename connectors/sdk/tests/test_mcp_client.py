from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))
observability_module = ModuleType("observability")
tracing_module = ModuleType("observability.tracing")


def _inject_trace_headers(headers: dict[str, str]) -> dict[str, str]:
    return headers


@contextmanager
def _start_agent_span(*_: Any, **__: Any) -> Any:
    yield None


tracing_module.inject_trace_headers = _inject_trace_headers
tracing_module.start_agent_span = _start_agent_span
observability_module.tracing = tracing_module
sys.modules.setdefault("observability", observability_module)
sys.modules.setdefault("observability.tracing", tracing_module)

import mcp_client
from base_connector import ConnectorCategory, ConnectorConfig
from mcp_client import (
    MCPClient,
    MCPResponseError,
    MCPServerError,
    MCPToolNotFoundError,
    MCPTransportError,
)


class StubClient:
    def __init__(
        self,
        response: httpx.Response,
        on_post: Callable[[str, dict[str, Any] | None, dict[str, str] | None], None] | None = None,
    ) -> None:
        self._response = response
        self._on_post = on_post

    def post(
        self, url: str, *, json: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> httpx.Response:
        if self._on_post:
            self._on_post(url, json, headers)
        return self._response

    def __enter__(self) -> "StubClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


def make_config(**overrides: Any) -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="connector-1",
        name="Test",
        category=ConnectorCategory.PM,
        mcp_server_url="https://mcp.example",
        **overrides,
    )


def stub_client_factory(
    response: httpx.Response,
    capture: dict[str, Any],
) -> Callable[..., StubClient]:
    def factory(*_: Any, **__: Any) -> StubClient:
        def on_post(url: str, payload: dict[str, Any] | None, headers: dict[str, str] | None) -> None:
            capture.update({"url": url, "payload": payload, "headers": headers})

        return StubClient(response, on_post=on_post)

    return factory


def test_mcp_client_list_tools_normalizes_response(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(
        200,
        json={"jsonrpc": "2.0", "id": "1", "result": {"tools": [{"name": "one"}]}},
    )
    capture: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "Client", stub_client_factory(response, capture))

    client = MCPClient(make_config())

    tools = client.list_tools()

    assert tools == [{"name": "one"}]
    assert capture["payload"]["method"] == "listTools"
    assert "params" not in capture["payload"]


def test_mcp_client_invoke_tool_maps_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(
        200,
        json={"jsonrpc": "2.0", "id": "1", "result": {"ok": True}},
    )
    capture: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "Client", stub_client_factory(response, capture))

    client = MCPClient(make_config(mcp_tool_map={"list_records": "records.list"}))

    result = client.call_tool("list_records", {"project_id": "abc"})

    assert result == {"ok": True}
    assert capture["payload"]["method"] == "invokeTool"
    assert capture["payload"]["params"] == {
        "name": "records.list",
        "arguments": {"project_id": "abc"},
    }


def test_mcp_client_auth_headers_include_config_and_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = httpx.Response(
        200,
        json={"jsonrpc": "2.0", "id": "1", "result": {"tools": []}},
    )
    capture: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "Client", stub_client_factory(response, capture))
    monkeypatch.setenv("MCP_OAUTH_TOKEN", "env-token")
    monkeypatch.setattr(mcp_client, "inject_trace_headers", lambda headers: headers)

    client = MCPClient(
        make_config(
            mcp_api_key="config-key",
            mcp_api_key_header="X-API-Key-Alt",
            mcp_oauth_token="",
        )
    )

    client.list_tools()

    headers = capture["headers"]
    assert headers["X-API-Key-Alt"] == "config-key"
    assert headers["Authorization"] == "Bearer env-token"


def test_mcp_client_handles_tool_mapping_missing() -> None:
    client = MCPClient(make_config(mcp_tool_map={"list_records": "records.list"}))

    with pytest.raises(MCPToolNotFoundError):
        client.call_tool("create_record", {"name": "oops"})


def test_mcp_client_raises_transport_error_on_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(401, text="unauthorized")
    capture: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "Client", stub_client_factory(response, capture))

    client = MCPClient(make_config())

    with pytest.raises(MCPTransportError, match="Unauthorized"):
        client.list_tools()


def test_mcp_client_raises_server_error_from_jsonrpc(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(
        200,
        json={
            "jsonrpc": "2.0",
            "id": "1",
            "error": {"message": "boom", "code": -32000, "data": {"detail": "x"}},
        },
    )
    capture: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "Client", stub_client_factory(response, capture))

    client = MCPClient(make_config())

    with pytest.raises(MCPServerError) as exc_info:
        client.list_tools()

    exc = exc_info.value
    assert exc.code == -32000
    assert exc.data == {"detail": "x"}


def test_mcp_client_raises_response_error_for_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(200, content=b"not-json")
    capture: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "Client", stub_client_factory(response, capture))

    client = MCPClient(make_config())

    with pytest.raises(MCPResponseError, match="Invalid JSON-RPC response"):
        client.list_tools()
