"""Integration fixtures for MCP test harnesses."""

from __future__ import annotations

import json
from typing import Any

import pytest

try:
    import httpx

    from connectors.mcp_client import client as async_mcp_module
except ImportError:  # httpx not installed — fixtures will be unavailable
    httpx = None  # type: ignore[assignment]
    async_mcp_module = None  # type: ignore[assignment]


class MockMcpServer:
    """Lightweight JSON-RPC MCP server harness for integration tests."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self._tools: list[dict[str, Any]] = []
        self._tool_results: dict[str, Any] = {}
        self._tool_schemas: dict[str, Any] = {}
        self._tool_errors: dict[str, dict[str, Any]] = {}

    @property
    def tools(self) -> list[dict[str, Any]]:
        return list(self._tools)

    def register_tool(
        self,
        name: str,
        *,
        result: Any | None = None,
        schema: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        self._tools.append(
            {
                "name": name,
                "description": f"Mock tool {name}",
                "inputSchema": {"type": "object"},
            }
        )
        if result is not None:
            self._tool_results[name] = result
        if schema is not None:
            self._tool_schemas[name] = schema
        if error is not None:
            self._tool_errors[name] = error

    def handler(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode()) if request.content else {}
        self.requests.append(payload)
        request_id = payload.get("id")
        method = payload.get("method")
        if method == "initialize":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"protocolVersion": "2025-06-18", "capabilities": {"tools": True}},
                },
            )
        if method in {"listTools", "tools/list"}:
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": request_id, "result": {"tools": self.tools}},
            )
        if method in {"getToolSchema", "tools/get"}:
            params = payload.get("params") or {}
            name = params.get("name")
            schema = self._tool_schemas.get(name)
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"schema": schema} if schema is not None else {},
                },
            )
        if method in {"invokeTool", "tools/call"}:
            params = payload.get("params") or {}
            tool_name = params.get("name")
            if tool_name in self._tool_errors:
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": self._tool_errors[tool_name],
                    },
                )
            if tool_name not in self._tool_results:
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": "Tool not found"},
                    },
                )
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": self._tool_results[tool_name],
                },
            )
        return httpx.Response(
            400,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32600, "message": "Invalid Request"},
            },
        )


@pytest.fixture
def mock_mcp_server(monkeypatch: pytest.MonkeyPatch) -> MockMcpServer:
    server = MockMcpServer()
    transport = httpx.MockTransport(server.handler)
    original_async_client = httpx.AsyncClient

    def patched_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(async_mcp_module.httpx, "AsyncClient", patched_async_client)
    return server
