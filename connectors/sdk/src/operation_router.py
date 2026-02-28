from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable

from base_connector import ConnectorConfig, ConnectorError, normalize_mcp_operation
from connectors.mcp_client.client import MCPClient
from connectors.mcp_client.errors import MCPClientError, MCPToolNotFoundError
from observability.metrics import build_mcp_fallback_metrics

logger = logging.getLogger(__name__)

class OperationRouter:
    def __init__(
        self, config: ConnectorConfig, *, mcp_client: MCPClient | None = None
    ) -> None:
        self.config = config
        self._mcp_client = mcp_client
        service_name = os.getenv("MCP_SERVICE_NAME", "mcp-client")
        self._fallback_metrics = build_mcp_fallback_metrics(service_name)

    def _record_fallback(self, operation: str, reason: str) -> None:
        attributes = {
            "service": os.getenv("MCP_SERVICE_NAME", "mcp-client"),
            "system": self.config.mcp_server_id or self.config.connector_id,
            "operation": operation,
            "reason": reason,
        }
        self._fallback_metrics.fallbacks.add(1, attributes)

    def should_use_mcp(self, operation: str) -> bool:
        if not self.config.prefer_mcp:
            return False
        if not self.config.mcp_server_url:
            return False
        if not self.config.is_mcp_enabled_for(operation):
            return False
        tool_map = self.config.mcp_tool_map or {}
        resolved = normalize_mcp_operation(operation)
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
            self._record_fallback(operation, "disabled_or_unmapped")
            try:
                return rest_call()
            except ConnectorError as exc:
                raise RuntimeError(
                    f"Operation {operation} failed via REST connector fallback: {exc}"
                ) from exc
        try:
            return mcp_call()
        except MCPToolNotFoundError as exc:
            logger.warning(
                "MCP tool not found for operation %s; falling back to REST. Error: %s",
                operation,
                exc,
            )
            self._record_fallback(operation, "tool_not_found")
            try:
                return rest_call()
            except ConnectorError as rest_exc:
                raise RuntimeError(
                    f"Operation {operation} failed after MCP tool-not-found fallback: {rest_exc}"
                ) from rest_exc
        except MCPClientError as exc:
            logger.warning(
                "MCP operation %s failed; falling back to REST. Error: %s",
                operation,
                exc,
            )
            self._record_fallback(operation, "client_error")
            try:
                return rest_call()
            except ConnectorError as rest_exc:
                raise RuntimeError(
                    f"Operation {operation} failed after MCP client-error fallback: {rest_exc}"
                ) from rest_exc
        except ValueError as exc:
            logger.warning(
                "MCP operation %s failed due to invalid configuration; falling back to REST. Error: %s",
                operation,
                exc,
            )
            self._record_fallback(operation, "invalid_config")
            try:
                return rest_call()
            except ConnectorError as rest_exc:
                raise RuntimeError(
                    f"Operation {operation} failed after MCP invalid-config fallback: {rest_exc}"
                ) from rest_exc

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
