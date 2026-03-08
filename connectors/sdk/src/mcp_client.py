"""MCP clients for invoking tool endpoints."""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from base_connector import ConnectorConfig

REPO_ROOT = Path(__file__).resolve().parents[3]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

from observability.metrics import build_mcp_client_metrics  # noqa: E402
from observability.tracing import inject_trace_headers, start_agent_span  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_API_KEY_HEADER = "X-API-Key"
DEFAULT_TRACE_SPAN = "connectors.sdk.mcp"
TraceHook = Callable[[str, dict[str, Any]], None | Coroutine[Any, Any, None]]


@dataclass(frozen=True)
class MCPAuthConfig:
    api_key: str | None = None
    api_key_header: str = DEFAULT_API_KEY_HEADER
    oauth_token: str | None = None

    @classmethod
    def from_env(cls) -> MCPAuthConfig:
        return cls(
            api_key=os.getenv("MCP_API_KEY"),
            api_key_header=os.getenv("MCP_API_KEY_HEADER", DEFAULT_API_KEY_HEADER),
            oauth_token=os.getenv("MCP_OAUTH_TOKEN"),
        )

    @classmethod
    def from_config(cls, config: ConnectorConfig) -> MCPAuthConfig:
        custom_fields = config.custom_fields or {}
        return cls(
            api_key=config.mcp_api_key or custom_fields.get("mcp_api_key"),
            api_key_header=(
                config.mcp_api_key_header
                or custom_fields.get("mcp_api_key_header", DEFAULT_API_KEY_HEADER)
            ),
            oauth_token=config.mcp_oauth_token or custom_fields.get("mcp_oauth_token"),
        )

    def with_fallback(self, other: MCPAuthConfig) -> MCPAuthConfig:
        return MCPAuthConfig(
            api_key=self.api_key or other.api_key,
            api_key_header=self.api_key_header or other.api_key_header,
            oauth_token=self.oauth_token or other.oauth_token,
        )

    def build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers[self.api_key_header or DEFAULT_API_KEY_HEADER] = self.api_key
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"
        return headers


class MCPClientError(RuntimeError):
    """Base MCP client error."""


class MCPTransportError(MCPClientError):
    """Transport error when calling MCP server."""


class MCPResponseError(MCPClientError):
    """Invalid MCP response payload."""


class MCPToolNotFoundError(MCPClientError):
    """Tool mapping missing for a requested operation."""


class MCPServerError(MCPClientError):
    """MCP server returned an error response."""

    def __init__(self, message: str, *, code: int | None = None, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data


class MCPAuthenticationError(MCPClientError):
    """Authentication failure when calling MCP server."""


class MCPClient:
    """Simple JSON-RPC MCP client built for connector usage."""

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        server_url: str | None = None,
        tool_map: dict[str, str] | None = None,
        timeout_s: float = 30.0,
        trace_hook: TraceHook | None = None,
        trace_span: str = DEFAULT_TRACE_SPAN,
        service_name: str | None = None,
    ) -> None:
        self._config = config
        self._base_url = server_url or config.mcp_server_url
        self._tool_map = tool_map or {k: v for k, v in (config.mcp_tool_map or {}).items()}
        self._timeout_s = timeout_s
        self._trace_hook = trace_hook
        self._trace_span = trace_span
        self._service_name = service_name or os.getenv("MCP_SERVICE_NAME", "mcp-client")
        self._fallback_decisions: dict[str, Any] = {
            "tool_map_fallback": tool_map is None,
            "url_override": bool(server_url),
        }
        self._auth = MCPAuthConfig.from_config(config).with_fallback(MCPAuthConfig.from_env())
        self._fallback_decisions["auth_from_config"] = bool(
            config.mcp_api_key
            or config.mcp_api_key_header
            or config.mcp_oauth_token
            or (config.custom_fields or {}).get("mcp_api_key")
            or (config.custom_fields or {}).get("mcp_oauth_token")
        )
        env_auth = MCPAuthConfig.from_env()
        self._fallback_decisions["auth_from_env"] = bool(env_auth.api_key or env_auth.oauth_token)
        self._metrics = build_mcp_client_metrics(self._service_name)
        if not self._base_url:
            raise ValueError("MCP server URL is required")

    @property
    def base_url(self) -> str:
        return self._base_url

    def has_tool(self, tool_key: str) -> bool:
        return bool(self._tool_map.get(tool_key))

    def list_tools(self) -> list[dict[str, Any]]:
        response = self._jsonrpc("listTools", None)
        tools_payload = response.get("tools") if isinstance(response, dict) else None
        if tools_payload is None:
            raise MCPResponseError("listTools response missing tools")
        if not isinstance(tools_payload, list):
            raise MCPResponseError("listTools response invalid tools payload")
        return tools_payload

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        payload = {"name": tool_name}
        response = self._jsonrpc("getToolSchema", payload)
        if not isinstance(response, dict):
            return None
        return response.get("schema") or response.get("tool") or response

    def call_tool(self, tool_key: str, params: dict[str, Any] | None = None) -> Any:
        tool_name = self._tool_map.get(tool_key)
        if not tool_name:
            raise MCPToolNotFoundError(f"Tool mapping missing for {tool_key}")
        return self.invoke_tool(tool_name, params)

    def invoke_tool(self, tool_name: str, params: dict[str, Any] | None = None) -> Any:
        payload = {
            "name": tool_name,
            "arguments": params or {},
        }
        return self._jsonrpc("invokeTool", payload)

    def list_records(self, params: dict[str, Any] | None = None) -> Any:
        return self.call_tool("list_records", params)

    def list(self, params: dict[str, Any] | None = None) -> Any:
        return self.list_records(params)

    def create_record(self, params: dict[str, Any] | None = None) -> Any:
        return self.call_tool("create_record", params)

    def create(self, params: dict[str, Any] | None = None) -> Any:
        return self.create_record(params)

    def update_record(self, params: dict[str, Any] | None = None) -> Any:
        return self.call_tool("update_record", params)

    def update(self, params: dict[str, Any] | None = None) -> Any:
        return self.update_record(params)

    def delete_record(self, params: dict[str, Any] | None = None) -> Any:
        return self.call_tool("delete_record", params)

    def delete(self, params: dict[str, Any] | None = None) -> Any:
        return self.delete_record(params)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        headers.update(self._auth.build_headers())
        return inject_trace_headers(headers)

    def _jsonrpc(self, method: str, params: dict[str, Any] | None) -> Any:
        request_id = str(uuid.uuid4())
        tool_name = params.get("name") if isinstance(params, dict) else None
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            body["params"] = params
        headers = self._build_headers()
        log_extra = {
            "system": self._config.mcp_server_id or self._config.connector_id,
            "tool_name": tool_name,
            "fallback_decisions": self._fallback_decisions,
            "method": method,
            "request_id": request_id,
        }
        logger.debug("mcp_request", extra=log_extra | {"url": self.base_url})
        self._emit_trace("request", {"method": method, "id": request_id, "url": self.base_url})
        start_time = time.perf_counter()
        outcome = "success"
        with start_agent_span(self._trace_span, {"mcp.method": method, "mcp.id": request_id}):
            try:
                with httpx.Client(timeout=self._timeout_s) as client:
                    response = client.post(self.base_url, json=body, headers=headers)
            except httpx.RequestError as exc:
                outcome = "error"
                self._record_metrics(method, tool_name, outcome, start_time)
                logger.warning("mcp_transport_error", extra=log_extra | {"error": str(exc)})
                raise MCPTransportError(str(exc)) from exc
        if response.status_code == 401:
            outcome = "error"
            self._record_metrics(method, tool_name, outcome, start_time)
            logger.warning("mcp_auth_error", extra=log_extra | {"status": response.status_code})
            raise MCPTransportError("Unauthorized MCP response")
        if response.status_code >= 400:
            outcome = "error"
            self._record_metrics(method, tool_name, outcome, start_time)
            logger.warning(
                "mcp_transport_error", extra=log_extra | {"status": response.status_code}
            )
            raise MCPTransportError(
                f"MCP server responded with status {response.status_code}: {response.text}"
            )
        try:
            payload = self._parse_response(response)
        except MCPResponseError as exc:
            outcome = "error"
            self._record_metrics(method, tool_name, outcome, start_time)
            logger.warning("mcp_response_error", extra=log_extra | {"error": str(exc)})
            raise
        self._emit_trace("response", {"method": method, "id": request_id, "error": payload.get("error")})
        if payload.get("error"):
            outcome = "error"
            self._record_metrics(method, tool_name, outcome, start_time)
            logger.warning("mcp_server_error", extra=log_extra | {"error": payload.get("error")})
            error = payload["error"]
            raise MCPServerError(
                error.get("message", "MCP server error"),
                code=error.get("code"),
                data=error.get("data"),
            )
        self._record_metrics(method, tool_name, outcome, start_time)
        logger.info(
            "mcp_response",
            extra=log_extra | {"status": response.status_code, "outcome": outcome},
        )
        return payload.get("result")

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise MCPResponseError("Invalid JSON-RPC response") from exc
        if not isinstance(payload, dict):
            raise MCPResponseError("Invalid JSON-RPC response format")
        return payload

    def _emit_trace(self, event: str, payload: dict[str, Any]) -> None:
        if not self._trace_hook:
            return
        result = self._trace_hook(event, payload)
        if asyncio.iscoroutine(result):
            asyncio.create_task(result)

    def _record_metrics(
        self, method: str, tool_name: str | None, outcome: str, start_time: float
    ) -> None:
        elapsed = time.perf_counter() - start_time
        attributes = {
            "service": self._service_name,
            "system": self._config.mcp_server_id or self._config.connector_id,
            "method": method,
            "tool_name": tool_name or "",
            "outcome": outcome,
        }
        self._metrics.requests.add(1, attributes)
        self._metrics.latency.record(elapsed, attributes)


class AsyncMCPClient(MCPClient):
    """Async JSON-RPC MCP client with tool helpers."""

    async def list_tools(self) -> list[dict[str, Any]]:
        response = await self._jsonrpc_async("listTools", None)
        tools_payload = response.get("tools") if isinstance(response, dict) else None
        if tools_payload is None:
            raise MCPResponseError("listTools response missing tools")
        if not isinstance(tools_payload, list):
            raise MCPResponseError("listTools response invalid tools payload")
        return tools_payload

    async def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        payload = {"name": tool_name}
        response = await self._jsonrpc_async("getToolSchema", payload)
        if not isinstance(response, dict):
            return None
        return response.get("schema") or response.get("tool") or response

    async def call_tool(self, tool_key: str, params: dict[str, Any] | None = None) -> Any:
        tool_name = self._tool_map.get(tool_key)
        if not tool_name:
            raise MCPToolNotFoundError(f"Tool mapping missing for {tool_key}")
        return await self.invoke_tool(tool_name, params)

    async def invoke_tool(self, tool_name: str, params: dict[str, Any] | None = None) -> Any:
        payload = {
            "name": tool_name,
            "arguments": params or {},
        }
        return await self._jsonrpc_async("invokeTool", payload)

    async def list_records(self, params: dict[str, Any] | None = None) -> Any:
        return await self.call_tool("list_records", params)

    async def list(self, params: dict[str, Any] | None = None) -> Any:
        return await self.list_records(params)

    async def create_record(self, params: dict[str, Any] | None = None) -> Any:
        return await self.call_tool("create_record", params)

    async def create(self, params: dict[str, Any] | None = None) -> Any:
        return await self.create_record(params)

    async def update_record(self, params: dict[str, Any] | None = None) -> Any:
        return await self.call_tool("update_record", params)

    async def update(self, params: dict[str, Any] | None = None) -> Any:
        return await self.update_record(params)

    async def delete_record(self, params: dict[str, Any] | None = None) -> Any:
        return await self.call_tool("delete_record", params)

    async def delete(self, params: dict[str, Any] | None = None) -> Any:
        return await self.delete_record(params)

    async def _jsonrpc_async(self, method: str, params: dict[str, Any] | None) -> Any:
        request_id = str(uuid.uuid4())
        tool_name = params.get("name") if isinstance(params, dict) else None
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            body["params"] = params
        headers = self._build_headers()
        log_extra = {
            "system": self._config.mcp_server_id or self._config.connector_id,
            "tool_name": tool_name,
            "fallback_decisions": self._fallback_decisions,
            "method": method,
            "request_id": request_id,
        }
        logger.debug("mcp_request", extra=log_extra | {"url": self.base_url})
        self._emit_trace("request", {"method": method, "id": request_id, "url": self.base_url})
        start_time = time.perf_counter()
        outcome = "success"
        with start_agent_span(self._trace_span, {"mcp.method": method, "mcp.id": request_id}):
            try:
                async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                    response = await client.post(self.base_url, json=body, headers=headers)
            except httpx.RequestError as exc:
                outcome = "error"
                self._record_metrics(method, tool_name, outcome, start_time)
                logger.warning("mcp_transport_error", extra=log_extra | {"error": str(exc)})
                raise MCPTransportError(str(exc)) from exc
        if response.status_code == 401:
            outcome = "error"
            self._record_metrics(method, tool_name, outcome, start_time)
            logger.warning("mcp_auth_error", extra=log_extra | {"status": response.status_code})
            raise MCPTransportError("Unauthorized MCP response")
        if response.status_code >= 400:
            outcome = "error"
            self._record_metrics(method, tool_name, outcome, start_time)
            logger.warning(
                "mcp_transport_error", extra=log_extra | {"status": response.status_code}
            )
            raise MCPTransportError(
                f"MCP server responded with status {response.status_code}: {response.text}"
            )
        try:
            payload = self._parse_response(response)
        except MCPResponseError as exc:
            outcome = "error"
            self._record_metrics(method, tool_name, outcome, start_time)
            logger.warning("mcp_response_error", extra=log_extra | {"error": str(exc)})
            raise
        self._emit_trace("response", {"method": method, "id": request_id, "error": payload.get("error")})
        if payload.get("error"):
            outcome = "error"
            self._record_metrics(method, tool_name, outcome, start_time)
            logger.warning("mcp_server_error", extra=log_extra | {"error": payload.get("error")})
            error = payload["error"]
            raise MCPServerError(
                error.get("message", "MCP server error"),
                code=error.get("code"),
                data=error.get("data"),
            )
        self._record_metrics(method, tool_name, outcome, start_time)
        logger.info(
            "mcp_response",
            extra=log_extra | {"status": response.status_code, "outcome": outcome},
        )
        return payload.get("result")
