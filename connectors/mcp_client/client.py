"""Async MCP client for invoking tools."""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import httpx

from integrations.connectors.sdk.src.base_connector import ConnectorConfig
from observability.metrics import build_mcp_client_metrics
from observability.tracing import inject_trace_headers, start_agent_span

from .auth import AuthConfig
from .errors import (
    MCPAuthenticationError,
    MCPResponseError,
    MCPServerError,
    MCPToolNotFoundError,
    MCPTransportError,
)
from .models import JsonRpcResponse, MCPPrompt, MCPResource, MCPToolSchema

TraceHook = Callable[[str, dict[str, Any]], None]
DEFAULT_TRACE_SPAN = "mcp.client"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"
METHOD_NOT_FOUND_CODE = -32601
DEFAULT_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
DEFAULT_RETRYABLE_ERROR_CODES = {-32000, -32001, -32002, -32003}

logger = logging.getLogger(__name__)


@dataclass
class MCPClientConfig:
    mcp_server_id: str
    mcp_server_url: str
    override_url: str | None = None
    tool_map: dict[str, str] = field(default_factory=dict)
    protocol_version: str = ""
    capabilities: dict[str, Any] = field(default_factory=dict)
    trace_hook: TraceHook | None = None
    trace_headers: dict[str, str] = field(default_factory=dict)
    timeout_s: float = 30.0
    max_retries: int = 3
    retry_backoff_s: float = 0.5
    retryable_status_codes: set[int] = field(
        default_factory=lambda: set(DEFAULT_RETRYABLE_STATUS_CODES)
    )
    retryable_error_codes: set[int] = field(
        default_factory=lambda: set(DEFAULT_RETRYABLE_ERROR_CODES)
    )
    auto_initialize: bool = True
    service_name: str | None = None
    trace_span: str = DEFAULT_TRACE_SPAN

    @classmethod
    def from_connector_config(
        cls,
        config: ConnectorConfig,
        override_url: str | None = None,
        trace_hook: TraceHook | None = None,
        trace_headers: dict[str, str] | None = None,
        service_name: str | None = None,
        trace_span: str = DEFAULT_TRACE_SPAN,
    ) -> "MCPClientConfig":
        return cls(
            mcp_server_id=config.mcp_server_id,
            mcp_server_url=config.mcp_server_url,
            override_url=override_url,
            tool_map={k: v for k, v in (config.mcp_tool_map or {}).items()},
            protocol_version=getattr(config, "protocol_version", ""),
            capabilities={
                "tools": True,
                "resources": True,
                "prompts": True,
                "tasks": True,
                "notifications": True,
            },
            trace_hook=trace_hook,
            trace_headers=trace_headers or {},
            service_name=service_name,
            trace_span=trace_span,
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
        protocol_version: str | None = None,
        capabilities: dict[str, Any] | None = None,
        trace_hook: TraceHook | None = None,
        trace_headers: dict[str, str] | None = None,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        retry_backoff_s: float = 0.5,
        retryable_status_codes: Iterable[int] | None = None,
        retryable_error_codes: Iterable[int] | None = None,
        auto_initialize: bool = True,
        service_name: str | None = None,
        trace_span: str = DEFAULT_TRACE_SPAN,
        notification_hook: TraceHook | None = None,
        tool_update_hook: Callable[[list[MCPToolSchema]], None] | None = None,
    ) -> None:
        self.mcp_server_id = mcp_server_id
        self.mcp_server_url = mcp_server_url
        self.override_url = override_url
        self._trace_hook = trace_hook
        self._notification_hook = notification_hook
        self._tool_update_hook = tool_update_hook
        self._trace_headers = trace_headers or {}
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._retry_backoff_s = retry_backoff_s
        self._retryable_status_codes = (
            set(retryable_status_codes) if retryable_status_codes else DEFAULT_RETRYABLE_STATUS_CODES
        )
        self._retryable_error_codes = (
            set(retryable_error_codes) if retryable_error_codes else DEFAULT_RETRYABLE_ERROR_CODES
        )
        self._auto_initialize = auto_initialize
        self._trace_span = trace_span
        self._service_name = service_name or os.getenv("MCP_SERVICE_NAME", "mcp-client")
        self._protocol_version = (
            protocol_version or os.getenv("MCP_PROTOCOL_VERSION") or DEFAULT_PROTOCOL_VERSION
        )
        self._capabilities = capabilities or {
            "tools": True,
            "resources": True,
            "prompts": True,
            "tasks": True,
            "notifications": True,
        }
        self._auth = auth or AuthConfig()
        self._fallback_decisions: dict[str, Any] = {
            "auth_fallback": auth is None,
            "tool_map_fallback": tool_map is None,
            "url_override": bool(override_url),
        }
        if config is not None:
            config_auth = AuthConfig.from_connector_config(config)
            self._auth = self._auth.with_fallback(AuthConfig.from_connector_config(config))
            self._auth = self._auth.with_fallback(AuthConfig.from_env())
            self._tool_map = tool_map or config.mcp_tool_map or {}
            self._fallback_decisions["auth_from_config"] = bool(
                config_auth.api_key
                or config_auth.oauth_token
                or config_auth.client_id
                or config_auth.client_secret
                or config_auth.scope
            )
        else:
            self._auth = self._auth.with_fallback(AuthConfig.from_env())
            self._tool_map = tool_map or {}
            self._fallback_decisions["auth_from_config"] = False
        env_auth = AuthConfig.from_env()
        self._fallback_decisions["auth_from_env"] = bool(
            env_auth.api_key
            or env_auth.oauth_token
            or env_auth.client_id
            or env_auth.client_secret
            or env_auth.scope
        )
        self._metrics = build_mcp_client_metrics(self._service_name)
        self._initialize_lock = asyncio.Lock()
        self._initialized = False
        self._server_capabilities: dict[str, Any] = {}
        self._cached_tools: list[MCPToolSchema] = []
        self._notification_handlers: dict[str, Callable[[dict[str, Any]], None]] = {}

    @property
    def base_url(self) -> str:
        return self.override_url or self.mcp_server_url

    @property
    def negotiated_protocol_version(self) -> str:
        return self._protocol_version

    @property
    def server_capabilities(self) -> dict[str, Any]:
        return self._server_capabilities

    def register_notification_handler(
        self, method: str, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        self._notification_handlers[method] = handler

    async def initialize(self) -> dict[str, Any]:
        payload = {
            "protocolVersion": self._protocol_version,
            "capabilities": self._capabilities,
            "clientInfo": {"name": self._service_name},
        }
        response = await self._jsonrpc("initialize", params=payload, skip_initialize=True)
        if not isinstance(response, dict):
            raise MCPResponseError("initialize response missing payload")
        server_version = response.get("protocolVersion") or response.get("version")
        if server_version and server_version != self._protocol_version:
            raise MCPResponseError(
                f"MCP protocol mismatch: server={server_version}, client={self._protocol_version}"
            )
        self._server_capabilities = response.get("capabilities", {}) or {}
        self._initialized = True
        return response

    async def list_resources(self) -> list[MCPResource]:
        response = await self._jsonrpc_with_fallback(["resources/list"], params=None)
        resources_payload = response.get("resources") if isinstance(response, dict) else None
        if resources_payload is None:
            raise MCPResponseError("resources/list response missing resources")
        return [MCPResource.from_dict(resource) for resource in resources_payload]

    async def get_resource(self, uri: str) -> Any:
        payload = {"uri": uri}
        return await self._jsonrpc_with_fallback(["resources/get"], params=payload)

    async def list_prompts(self) -> list[MCPPrompt]:
        response = await self._jsonrpc_with_fallback(["prompts/list"], params=None)
        prompts_payload = response.get("prompts") if isinstance(response, dict) else None
        if prompts_payload is None:
            raise MCPResponseError("prompts/list response missing prompts")
        return [MCPPrompt.from_dict(prompt) for prompt in prompts_payload]

    async def get_prompt(self, name: str) -> Any:
        payload = {"name": name}
        return await self._jsonrpc_with_fallback(["prompts/get"], params=payload)

    async def call_prompt(self, name: str, params: dict[str, Any] | None = None) -> Any:
        payload = {"name": name, "arguments": params or {}}
        return await self._jsonrpc_with_fallback(["prompts/call"], params=payload)

    async def create_task(self, name: str, params: dict[str, Any] | None = None) -> Any:
        payload = {"name": name, "arguments": params or {}}
        return await self._jsonrpc_with_fallback(["tasks/create"], params=payload)

    async def get_task(self, task_id: str) -> Any:
        payload = {"id": task_id}
        return await self._jsonrpc_with_fallback(["tasks/get"], params=payload)

    async def cancel_task(self, task_id: str) -> Any:
        payload = {"id": task_id}
        return await self._jsonrpc_with_fallback(["tasks/cancel"], params=payload)

    async def discover(self) -> list[MCPToolSchema]:
        return await self.list_tools()

    async def list_tools(self) -> list[MCPToolSchema]:
        response = await self._jsonrpc_with_fallback(["tools/list", "listTools"], params=None)
        tools_payload = response.get("tools") if isinstance(response, dict) else None
        if tools_payload is None:
            raise MCPResponseError("tools/list response missing tools")
        self._cached_tools = [MCPToolSchema.from_dict(tool) for tool in tools_payload]
        return list(self._cached_tools)

    async def get_tool_schema(self, tool_name: str) -> Any:
        payload = {"name": tool_name}
        return await self._jsonrpc_with_fallback(["tools/get", "getToolSchema"], params=payload)

    async def invoke_tool(self, tool_name: str, params: dict[str, Any] | None = None) -> Any:
        payload = {
            "name": tool_name,
            "arguments": params or {},
        }
        return await self._jsonrpc_with_fallback(["tools/call", "invokeTool"], params=payload)

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

    async def _jsonrpc_with_fallback(
        self, methods: Iterable[str], params: dict[str, Any] | None
    ) -> Any:
        last_error: MCPServerError | None = None
        method_list = list(methods)
        for method in method_list:
            try:
                return await self._jsonrpc(method, params)
            except MCPServerError as exc:
                if exc.code == METHOD_NOT_FOUND_CODE and method != method_list[-1]:
                    last_error = exc
                    continue
                raise
        if last_error:
            raise last_error
        raise MCPResponseError("No MCP methods available for fallback")

    async def _ensure_initialized(self) -> None:
        if self._initialized or not self._auto_initialize:
            return
        async with self._initialize_lock:
            if self._initialized:
                return
            await self.initialize()

    async def _jsonrpc(
        self, method: str, params: dict[str, Any] | None, *, skip_initialize: bool = False
    ) -> Any:
        if method != "initialize" and not skip_initialize:
            await self._ensure_initialized()
        request_id = str(uuid.uuid4())
        tool_name = params.get("name") if isinstance(params, dict) else None
        body = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            body["params"] = params
        headers = {"Content-Type": "application/json", **self._auth.build_headers()}
        headers.update(self._trace_headers)
        headers = inject_trace_headers(headers)
        log_extra = {
            "system": self.mcp_server_id,
            "tool_name": tool_name,
            "fallback_decisions": self._fallback_decisions,
            "method": method,
            "request_id": request_id,
        }
        logger.debug("mcp_request", extra=log_extra | {"url": self.base_url})
        self._emit_trace("request", {"method": method, "id": request_id, "url": self.base_url})
        start_time = time.perf_counter()
        outcome = "success"
        attempt = 0
        while True:
            try:
                with start_agent_span(
                    self._trace_span, {"mcp.method": method, "mcp.id": request_id}
                ):
                    async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                        response = await client.post(self.base_url, json=body, headers=headers)
            except httpx.RequestError as exc:
                if attempt < self._max_retries:
                    await self._backoff(attempt)
                    attempt += 1
                    continue
                outcome = "error"
                self._record_metrics(method, tool_name, outcome, start_time)
                logger.warning("mcp_transport_error", extra=log_extra | {"error": str(exc)})
                raise MCPTransportError(str(exc)) from exc
            if response.status_code == 401:
                outcome = "error"
                self._record_metrics(method, tool_name, outcome, start_time)
                logger.warning("mcp_auth_error", extra=log_extra | {"status": response.status_code})
                raise MCPAuthenticationError("Unauthorized MCP response")
            if response.status_code in self._retryable_status_codes and attempt < self._max_retries:
                await self._backoff(attempt)
                attempt += 1
                continue
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
                payload = response.json()
            except ValueError as exc:
                if attempt < self._max_retries:
                    await self._backoff(attempt)
                    attempt += 1
                    continue
                outcome = "error"
                self._record_metrics(method, tool_name, outcome, start_time)
                logger.warning("mcp_response_error", extra=log_extra | {"error": str(exc)})
                raise MCPResponseError("Invalid JSON-RPC response") from exc
            rpc = JsonRpcResponse.from_dict(payload)
            self._emit_trace(
                "response", {"method": method, "id": request_id, "error": rpc.error}
            )
            if rpc.error:
                if (
                    rpc.error.code in self._retryable_error_codes
                    and attempt < self._max_retries
                ):
                    await self._backoff(attempt)
                    attempt += 1
                    continue
                outcome = "error"
                self._record_metrics(method, tool_name, outcome, start_time)
                logger.warning("mcp_server_error", extra=log_extra | {"error": rpc.error.message})
                raise MCPServerError(rpc.error.message, code=rpc.error.code, data=rpc.error.data)
            break
        self._record_metrics(method, tool_name, outcome, start_time)
        logger.info(
            "mcp_response",
            extra=log_extra | {"status": response.status_code, "outcome": outcome},
        )
        await self._handle_notifications(payload)
        return rpc.result

    def _record_metrics(
        self, method: str, tool_name: str | None, outcome: str, start_time: float
    ) -> None:
        elapsed = time.perf_counter() - start_time
        attributes = {
            "service": self._service_name,
            "system": self.mcp_server_id,
            "method": method,
            "tool_name": tool_name or "",
            "outcome": outcome,
        }
        self._metrics.requests.add(1, attributes)
        self._metrics.latency.record(elapsed, attributes)

    def _emit_trace(self, event: str, payload: dict[str, Any]) -> None:
        if not self._trace_hook:
            return
        if asyncio.iscoroutinefunction(self._trace_hook):
            asyncio.create_task(self._trace_hook(event, payload))
        else:
            self._trace_hook(event, payload)

    async def _backoff(self, attempt: int) -> None:
        delay = self._retry_backoff_s * (2**attempt)
        await asyncio.sleep(delay)

    async def _handle_notifications(self, payload: dict[str, Any]) -> None:
        notifications = payload.get("notifications")
        if not notifications:
            return
        for notification in notifications:
            if not isinstance(notification, dict):
                continue
            await self.handle_notification(notification)

    async def handle_notification(self, notification: dict[str, Any]) -> None:
        method = notification.get("method")
        params = notification.get("params", {})
        if method in {"toolUpdate", "tools/updated"}:
            tools = await self.list_tools()
            if self._tool_update_hook:
                self._tool_update_hook(tools)
        handler = self._notification_handlers.get(method)
        if handler:
            handler(params if isinstance(params, dict) else {"data": params})
        if self._notification_hook:
            self._notification_hook(method or "notification", notification)
