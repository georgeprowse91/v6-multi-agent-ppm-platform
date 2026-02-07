"""Synchronous MCP client for invoking tool endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

from base_connector import ConnectorConfig

logger = logging.getLogger(__name__)

DEFAULT_API_KEY_HEADER = "X-API-Key"


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


class MCPClient:
    """Simple JSON-RPC MCP client built for connector usage."""

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        server_url: str | None = None,
        tool_map: dict[str, str] | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._config = config
        self._base_url = server_url or config.mcp_server_url
        self._tool_map = tool_map or {k: v for k, v in (config.mcp_tool_map or {}).items()}
        self._timeout_s = timeout_s
        if not self._base_url:
            raise ValueError("MCP server URL is required")

    @property
    def base_url(self) -> str:
        return self._base_url

    def has_tool(self, tool_key: str) -> bool:
        return bool(self._tool_map.get(tool_key))

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

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._config.mcp_api_key:
            header_name = (
                (self._config.custom_fields or {}).get("mcp_api_key_header")
                or DEFAULT_API_KEY_HEADER
            )
            headers[header_name] = self._config.mcp_api_key
        oauth_token = (self._config.custom_fields or {}).get("mcp_oauth_token")
        if oauth_token:
            headers["Authorization"] = f"Bearer {oauth_token}"
        return headers

    def _jsonrpc(self, method: str, params: dict[str, Any] | None) -> Any:
        request_id = str(uuid.uuid4())
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            body["params"] = params
        headers = self._build_headers()
        logger.debug("mcp_request", extra={"method": method, "id": request_id, "url": self.base_url})
        try:
            with httpx.Client(timeout=self._timeout_s) as client:
                response = client.post(self.base_url, json=body, headers=headers)
        except httpx.RequestError as exc:
            raise MCPTransportError(str(exc)) from exc
        if response.status_code >= 400:
            raise MCPTransportError(
                f"MCP server responded with status {response.status_code}: {response.text}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise MCPResponseError("Invalid JSON-RPC response") from exc
        if not isinstance(payload, dict):
            raise MCPResponseError("Invalid JSON-RPC response format")
        if payload.get("error"):
            error = payload["error"]
            raise MCPServerError(
                error.get("message", "MCP server error"),
                code=error.get("code"),
                data=error.get("data"),
            )
        return payload.get("result")
