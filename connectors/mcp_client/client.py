"""Async MCP client for invoking tools."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from connectors.sdk.src.base_connector import ConnectorConfig

from .auth import AuthConfig
from .errors import (
    MCPAuthenticationError,
    MCPResponseError,
    MCPServerError,
    MCPToolNotFoundError,
    MCPTransportError,
)
from .models import JsonRpcResponse, MCPToolSchema

TraceHook = Callable[[str, dict[str, Any]], None]


@dataclass
class MCPClientConfig:
    mcp_server_id: str
    mcp_server_url: str
    override_url: str | None = None
    tool_map: dict[str, str] = field(default_factory=dict)
    trace_hook: TraceHook | None = None
    trace_headers: dict[str, str] = field(default_factory=dict)
    timeout_s: float = 30.0

    @classmethod
    def from_connector_config(
        cls,
        config: ConnectorConfig,
        override_url: str | None = None,
        trace_hook: TraceHook | None = None,
        trace_headers: dict[str, str] | None = None,
    ) -> "MCPClientConfig":
        return cls(
            mcp_server_id=config.mcp_server_id,
            mcp_server_url=config.mcp_server_url,
            override_url=override_url,
            tool_map={k: v for k, v in (config.mcp_tool_map or {}).items()},
            trace_hook=trace_hook,
            trace_headers=trace_headers or {},
        )


class MCPClient:
    """Async MCP client implementing JSON-RPC tool invocation."""

    def __init__(
        self,
        mcp_server_id: str,
        mcp_server_url: str,
        *,
        override_url: str | None = None,
        auth: AuthConfig | None = None,
        config: ConnectorConfig | None = None,
        tool_map: dict[str, str] | None = None,
        trace_hook: TraceHook | None = None,
        trace_headers: dict[str, str] | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.mcp_server_id = mcp_server_id
        self.mcp_server_url = mcp_server_url
        self.override_url = override_url
        self._trace_hook = trace_hook
        self._trace_headers = trace_headers or {}
        self._timeout_s = timeout_s
        self._auth = auth or AuthConfig()
        if config is not None:
            self._auth = self._auth.with_fallback(AuthConfig.from_connector_config(config))
            self._auth = self._auth.with_fallback(AuthConfig.from_env())
            self._tool_map = tool_map or config.mcp_tool_map or {}
        else:
            self._auth = self._auth.with_fallback(AuthConfig.from_env())
            self._tool_map = tool_map or {}

    @property
    def base_url(self) -> str:
        return self.override_url or self.mcp_server_url

    async def discover(self) -> list[MCPToolSchema]:
        return await self.list_tools()

    async def list_tools(self) -> list[MCPToolSchema]:
        response = await self._jsonrpc("listTools", params=None)
        tools_payload = response.get("tools") if isinstance(response, dict) else None
        if tools_payload is None:
            raise MCPResponseError("listTools response missing tools")
        return [MCPToolSchema.from_dict(tool) for tool in tools_payload]

    async def invoke_tool(self, tool_name: str, params: dict[str, Any] | None = None) -> Any:
        payload = {
            "name": tool_name,
            "arguments": params or {},
        }
        return await self._jsonrpc("invokeTool", params=payload)

    async def list_records(self, params: dict[str, Any] | None = None) -> Any:
        return await self._invoke_from_map("list_records", params)

    async def create_record(self, params: dict[str, Any] | None = None) -> Any:
        return await self._invoke_from_map("create_record", params)

    async def update_record(self, params: dict[str, Any] | None = None) -> Any:
        return await self._invoke_from_map("update_record", params)

    async def delete_record(self, params: dict[str, Any] | None = None) -> Any:
        return await self._invoke_from_map("delete_record", params)

    async def _invoke_from_map(self, operation: str, params: dict[str, Any] | None) -> Any:
        tool_name = self._tool_map.get(operation)
        if not tool_name:
            raise MCPToolNotFoundError(f"Tool mapping missing for {operation}")
        return await self.invoke_tool(tool_name, params)

    async def _jsonrpc(self, method: str, params: dict[str, Any] | None) -> Any:
        request_id = str(uuid.uuid4())
        body = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            body["params"] = params
        headers = {"Content-Type": "application/json", **self._auth.build_headers()}
        headers.update(self._trace_headers)
        self._emit_trace("request", {"method": method, "id": request_id, "url": self.base_url})
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(self.base_url, json=body, headers=headers)
        except httpx.RequestError as exc:
            raise MCPTransportError(str(exc)) from exc
        if response.status_code == 401:
            raise MCPAuthenticationError("Unauthorized MCP response")
        if response.status_code >= 400:
            raise MCPTransportError(
                f"MCP server responded with status {response.status_code}: {response.text}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise MCPResponseError("Invalid JSON-RPC response") from exc
        rpc = JsonRpcResponse.from_dict(payload)
        self._emit_trace("response", {"method": method, "id": request_id, "error": rpc.error})
        if rpc.error:
            raise MCPServerError(rpc.error.message, code=rpc.error.code, data=rpc.error.data)
        return rpc.result

    def _emit_trace(self, event: str, payload: dict[str, Any]) -> None:
        if not self._trace_hook:
            return
        if asyncio.iscoroutinefunction(self._trace_hook):
            asyncio.create_task(self._trace_hook(event, payload))
        else:
            self._trace_hook(event, payload)
