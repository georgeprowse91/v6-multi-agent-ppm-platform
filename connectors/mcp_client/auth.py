"""Authentication helpers for MCP client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from integrations.connectors.sdk.src.base_connector import ConnectorConfig

DEFAULT_API_KEY_HEADER = "X-API-Key"


@dataclass
class AuthConfig:
    """Authentication configuration for MCP servers."""

    api_key: str | None = None
    api_key_header: str = DEFAULT_API_KEY_HEADER
    oauth_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scope: str | None = None

    @classmethod
    def from_env(cls) -> "AuthConfig":
        return cls(
            api_key=os.getenv("MCP_API_KEY"),
            api_key_header=os.getenv("MCP_API_KEY_HEADER", DEFAULT_API_KEY_HEADER),
            oauth_token=os.getenv("MCP_OAUTH_TOKEN"),
            client_id=os.getenv("MCP_CLIENT_ID"),
            client_secret=os.getenv("MCP_CLIENT_SECRET"),
            scope=os.getenv("MCP_SCOPE"),
        )

    @classmethod
    def from_connector_config(cls, config: ConnectorConfig) -> "AuthConfig":
        custom_fields: dict[str, Any] = config.custom_fields or {}
        return cls(
            api_key=custom_fields.get("mcp_api_key"),
            api_key_header=custom_fields.get("mcp_api_key_header", DEFAULT_API_KEY_HEADER),
            oauth_token=custom_fields.get("mcp_oauth_token"),
            client_id=custom_fields.get("mcp_client_id"),
            client_secret=custom_fields.get("mcp_client_secret"),
            scope=custom_fields.get("mcp_scope"),
        )

    def with_fallback(self, other: "AuthConfig") -> "AuthConfig":
        return AuthConfig(
            api_key=self.api_key or other.api_key,
            api_key_header=self.api_key_header or other.api_key_header,
            oauth_token=self.oauth_token or other.oauth_token,
            client_id=self.client_id or other.client_id,
            client_secret=self.client_secret or other.client_secret,
            scope=self.scope or other.scope,
        )

    def build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers[self.api_key_header or DEFAULT_API_KEY_HEADER] = self.api_key
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"
        return headers
