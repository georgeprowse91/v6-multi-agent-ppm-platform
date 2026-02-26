"""
Microsoft Teams Connector Implementation.

Supports:
- OAuth2 authentication
- Reading teams and channels
- Writing messages
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_COMMON_SRC = _REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from mcp_client import MCPClient, MCPClientError  # noqa: E402
from rest_connector import OAuth2RestConnector  # noqa: E402
from connector_secrets import fetch_keyvault_secret, resolve_secret  # noqa: E402
try:
    from .mappers import map_from_mcp_response, map_to_mcp_params
except ImportError:
    from mappers import map_from_mcp_response, map_to_mcp_params

DEFAULT_TEAMS_URL = "https://graph.microsoft.com/v1.0"

logger = logging.getLogger(__name__)


class TeamsConnector(OAuth2RestConnector):
    CONNECTOR_ID = "teams"
    CONNECTOR_NAME = "Microsoft Teams"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = True
    IDEMPOTENCY_FIELDS = ("id", "message_id", "external_id")
    CONFLICT_TIMESTAMP_FIELD = "lastModifiedDateTime"

    INSTANCE_URL_ENV = "TEAMS_API_URL"
    CLIENT_ID_ENV = "TEAMS_CLIENT_ID"
    CLIENT_SECRET_ENV = "TEAMS_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "TEAMS_REFRESH_TOKEN"
    TOKEN_URL_ENV = "TEAMS_TOKEN_URL"
    DEFAULT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    SCOPES_ENV = "TEAMS_SCOPES"
    KEYVAULT_URL_ENV = "TEAMS_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "TEAMS_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "TEAMS_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "TEAMS_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/me/joinedTeams"
    AUTH_TEST_PARAMS = {"$top": 1}
    RESOURCE_PATHS = {
        "teams": {"path": "/me/joinedTeams", "items_path": "value"},
        "channels": {"path": "/teams/{team_id}/channels", "items_path": "value"},
        "messages": {
            "path": "/teams/{team_id}/channels/{channel_id}/messages",
            "items_path": "value",
            "write_path": "/teams/{team_id}/channels/{channel_id}/messages",
            "write_method": "POST",
        },
    }
    SCHEMA = {
        "teams": {"id": "string", "displayName": "string"},
        "channels": {"id": "string", "displayName": "string"},
        "messages": {"id": "string", "body": "string"},
    }

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        if not instance_url:
            instance_url = DEFAULT_TEAMS_URL
        keyvault_url = resolve_secret(os.getenv(self.KEYVAULT_URL_ENV))
        client_id = resolve_secret(os.getenv(self.CLIENT_ID_ENV))
        client_secret = resolve_secret(os.getenv(self.CLIENT_SECRET_ENV))
        refresh_token = resolve_secret(os.getenv(self.REFRESH_TOKEN_ENV))
        client_id_secret = resolve_secret(os.getenv(self.CLIENT_ID_SECRET_ENV))
        client_secret_secret = resolve_secret(os.getenv(self.CLIENT_SECRET_SECRET_ENV))
        refresh_token_secret = resolve_secret(os.getenv(self.REFRESH_TOKEN_SECRET_ENV))
        client_id = (
            fetch_keyvault_secret(keyvault_url, client_id_secret) if client_id_secret else client_id
        ) or client_id
        client_secret = (
            fetch_keyvault_secret(keyvault_url, client_secret_secret)
            if client_secret_secret
            else client_secret
        ) or client_secret
        refresh_token = (
            fetch_keyvault_secret(keyvault_url, refresh_token_secret)
            if refresh_token_secret
            else refresh_token
        ) or refresh_token
        if not client_id or not client_secret or not refresh_token:
            raise ValueError(
                f"{self.CLIENT_ID_ENV}, {self.CLIENT_SECRET_ENV}, and {self.REFRESH_TOKEN_ENV} are required"
            )
        return instance_url, client_id, client_secret, refresh_token

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
        self._mcp_client: MCPClient | None = None
        self._mcp_tool_map = {
            "list_teams": "teams.listTeams",
            "list_channels": "teams.listChannels",
            "post_message": "teams.postMessage",
            **(config.mcp_tool_map or {}),
        }

    def _build_mcp_client(self) -> MCPClient:
        if self._mcp_client:
            return self._mcp_client
        if not self.config.mcp_server_url:
            raise ValueError("Teams MCP server URL is required")
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
                "MCP tool mapping missing for %s; falling back to REST for Teams.",
                tool_key,
            )
            return rest_call()
        try:
            client = self._build_mcp_client()
            payload = self._run_mcp(client.invoke_tool(tool_name, params))
            return response_mapper(payload)
        except (MCPClientError, ValueError) as exc:
            logger.warning(
                "MCP %s failed for Teams connector; falling back to REST. Error: %s",
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
            "teams": "list_teams",
            "channels": "list_channels",
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
