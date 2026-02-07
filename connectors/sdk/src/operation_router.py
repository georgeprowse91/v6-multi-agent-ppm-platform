from __future__ import annotations

import asyncio
from typing import Any, Callable

from base_connector import ConnectorConfig
from connectors.mcp_client.client import MCPClient
from connectors.mcp_client.errors import MCPToolNotFoundError

MCP_OPERATION_ALIASES = {
    "read": "list_records",
    "list": "list_records",
    "write": "create_record",
    "create": "create_record",
    "update": "update_record",
    "delete": "delete_record",
}


def resolve_mcp_operation(operation: str) -> str:
    normalized = operation.strip().lower()
    return MCP_OPERATION_ALIASES.get(normalized, normalized)


class OperationRouter:
    def __init__(
        self, config: ConnectorConfig, *, mcp_client: MCPClient | None = None
    ) -> None:
        self.config = config
        self._mcp_client = mcp_client

    def should_use_mcp(self, operation: str) -> bool:
        if not self.config.prefer_mcp:
            return False
        if not self.config.mcp_server_url:
            return False
        tool_map = self.config.mcp_tool_map or {}
        resolved = resolve_mcp_operation(operation)
        return bool(tool_map.get(resolved))

    def build_mcp_client(self) -> MCPClient:
        if self._mcp_client:
            return self._mcp_client
        if not self.config.mcp_server_url:
            raise ValueError("MCP server URL is required")
        self._mcp_client = MCPClient(
            mcp_server_id=self.config.mcp_server_id or self.config.connector_id,
            mcp_server_url=self.config.mcp_server_url,
            config=self.config,
        )
        return self._mcp_client

    def run(
        self,
        operation: str,
        *,
        mcp_call: Callable[[], Any],
        rest_call: Callable[[], Any],
    ) -> Any:
        if not self.should_use_mcp(operation):
            return rest_call()
        try:
            return mcp_call()
        except MCPToolNotFoundError:
            return rest_call()

    def run_mcp(self, coroutine: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()

    def extract_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("records", "items", "values", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return []
