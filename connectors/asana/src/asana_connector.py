"""
Asana Connector Implementation.

Supports:
- Bearer token authentication
- Reading projects and tasks
- Writing tasks
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

DEFAULT_ASANA_URL = "https://app.asana.com/api/1.0"


class AsanaConnector(RestConnector):
    CONNECTOR_ID = "asana"
    CONNECTOR_NAME = "Asana"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.PM
    SUPPORTS_WRITE = True

    AUTH_TEST_ENDPOINT = "/projects"
    AUTH_TEST_PARAMS = {"limit": 1}
    RESOURCE_PATHS = {
        "projects": {"path": "/projects", "items_path": "data"},
        "tasks": {"path": "/tasks", "items_path": "data", "write_path": "/tasks"},
    }
    SCHEMA = {
        "projects": {"gid": "string", "name": "string"},
        "tasks": {"gid": "string", "name": "string", "completed": "boolean"},
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
        instance_url = resolve_secret(os.getenv("ASANA_INSTANCE_URL")) or self.config.instance_url
        token = resolve_secret(os.getenv("ASANA_ACCESS_TOKEN"))
        if not instance_url:
            instance_url = DEFAULT_ASANA_URL
        if not token:
            raise ValueError("ASANA_ACCESS_TOKEN environment variable is required")
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
            rate_limit_per_minute=300,
            retry_config=retry_config,
            transport=self._transport,
        )
        return self._client
