"""
Slack Connector Implementation.

Supports:
- Bot token authentication
- Reading channels and users
- Writing messages
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from http_client import HttpClient, RetryConfig
from rest_connector import RestConnector
from secrets import resolve_secret

DEFAULT_SLACK_URL = "https://slack.com/api"


class SlackConnector(RestConnector):
    CONNECTOR_ID = "slack"
    CONNECTOR_NAME = "Slack"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = True

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
