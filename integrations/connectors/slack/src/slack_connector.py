"""
Slack Connector Implementation.

Supports:
- Bot token authentication
- Reading channels and users
- Writing messages
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from http_client import HttpClient, RetryConfig
from mcp_client import MCPClient, MCPClientError
from rest_connector import RestConnector
from secrets import resolve_secret
from .mappers import map_from_mcp_response, map_to_mcp_params

DEFAULT_SLACK_URL = "https://slack.com/api"

logger = logging.getLogger(__name__)


class SlackConnector(RestConnector):
    CONNECTOR_ID = "slack"
    CONNECTOR_NAME = "Slack"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = True
    IDEMPOTENCY_FIELDS = ("ts", "client_msg_id", "channel")
    CONFLICT_TIMESTAMP_FIELD = "ts"

    AUTH_TEST_ENDPOINT = "/auth.test"
    RESOURCE_PATHS = {
        "channels": {"path": "/conversations.list", "items_path": "channels"},
        "users": {"path": "/users.list", "items_path": "members"},
        "messages": {"path": "/chat.postMessage", "items_path": "message", "write_path": "/chat.postMessage"},
    }
    SCHEMA = {
        "channels": {"id": "string", "name": "string"},
        "users": {"id": "string", "name": "string"},
        "messages": {"ts": "string", "text": "string"},
    }

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        client: HttpClient | None = None,
        transport: Any | None = None,
    ) -> None:
        super().__init__(config, client=client, transport=transport)
        self._mcp_client: MCPClient | None = None
        self._mcp_tool_map = {
            "list_channels": "slack.listChannels",
            "list_users": "slack.listUsers",
            "post_message": "slack.postMessage",
            **(config.mcp_tool_map or {}),
        }

    def _get_credentials(self) -> tuple[str, str]:
        instance_url = resolve_secret(os.getenv("SLACK_API_URL")) or self.config.instance_url
        if not instance_url:
            instance_url = DEFAULT_SLACK_URL
        token = resolve_secret(os.getenv("SLACK_BOT_TOKEN"))
        if not token:
            raise ValueError("SLACK_BOT_TOKEN environment variable is required")
        return instance_url, token

    def _build_client(self) -> HttpClient:
        if self._client:
            return self._client
        instance_url, token = self._get_credentials()
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        self._client = HttpClient(
            base_url=instance_url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=30.0,
            rate_limit_per_minute=60,
            retry_config=retry_config,
            transport=self._transport,
        )
        return self._client

    def _build_mcp_client(self) -> MCPClient:
        if self._mcp_client:
            return self._mcp_client
        if not self.config.mcp_server_url:
            raise ValueError("Slack MCP server URL is required")
        self._mcp_client = MCPClient(
            mcp_server_id=self.config.mcp_server_id or self.CONNECTOR_ID,
            mcp_server_url=self.config.mcp_server_url,
            config=self.config,
        )
        return self._mcp_client

    def _run_mcp(self, coroutine: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()

    def _should_use_mcp(self, tool_key: str) -> bool:
        if not self.config.prefer_mcp:
            return False
        if not self.config.mcp_server_url:
            return False
        if not self.config.is_mcp_enabled_for(tool_key):
            return False
        return True

    def _try_mcp_then_rest(
        self,
        *,
        tool_key: str,
        params: dict[str, Any],
        rest_call: Any,
        response_mapper: Any,
    ) -> list[dict[str, Any]]:
        tool_name = self._mcp_tool_map.get(tool_key)
        if not self._should_use_mcp(tool_key):
            return rest_call()
        if not tool_name:
            logger.warning(
                "MCP tool mapping missing for %s; falling back to REST for Slack.",
                tool_key,
            )
            return rest_call()
        try:
            client = self._build_mcp_client()
            payload = self._run_mcp(client.invoke_tool(tool_name, params))
            return response_mapper(payload)
        except (MCPClientError, ValueError) as exc:
            logger.warning(
                "MCP %s failed for Slack connector; falling back to REST. Error: %s",
                tool_key,
                exc,
            )
            return rest_call()

    def read(
        self,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        read_tools = {
            "channels": "list_channels",
            "users": "list_users",
        }
        tool_key = read_tools.get(resource_type)
        rest_call = lambda: super().read(resource_type, filters=filters, limit=limit, offset=offset)
        if not tool_key:
            return rest_call()
        params = map_to_mcp_params(
            "list",
            {
                "resource_type": resource_type,
                "filters": filters or {},
                "limit": limit,
                "offset": offset,
            },
        )
        return self._try_mcp_then_rest(
            tool_key=tool_key,
            params=params,
            rest_call=rest_call,
            response_mapper=lambda payload: map_from_mcp_response("list", payload),
        )

    def write(
        self,
        resource_type: str,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        write_tools = {
            "messages": "post_message",
        }
        tool_key = write_tools.get(resource_type)
        rest_call = lambda: super().write(resource_type, data)
        if not tool_key:
            return rest_call()
        params = map_to_mcp_params("write", {"resource_type": resource_type, "records": data})
        return self._try_mcp_then_rest(
            tool_key=tool_key,
            params=params,
            rest_call=rest_call,
            response_mapper=lambda payload: map_from_mcp_response("write", payload),
        )
