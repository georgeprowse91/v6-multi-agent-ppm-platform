"""
Azure Communication Services Connector Implementation.

Supports:
- Connection string or API key authentication
- Sending SMS and email payloads
"""

from __future__ import annotations

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
from http_client import HttpClient, RetryConfig  # noqa: E402
from rest_connector import RestConnector  # noqa: E402
from connector_secrets import resolve_secret  # noqa: E402

DEFAULT_ACS_ENDPOINT = "https://communication.azure.com"


class AzureCommunicationServicesConnector(RestConnector):
    CONNECTOR_ID = "azure_communication_services"
    CONNECTOR_NAME = "Azure Communication Services"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = True

    AUTH_TEST_ENDPOINT = "/sms"
    RESOURCE_PATHS = {
        "sms": {
            "path": "/sms",
            "items_path": "value",
            "write_path": "/sms",
            "write_method": "POST",
        },
        "email": {
            "path": "/emails:send",
            "items_path": "value",
            "write_path": "/emails:send",
            "write_method": "POST",
        },
    }
    SCHEMA = {
        "sms": {"messageId": "string"},
        "email": {"messageId": "string"},
    }
    RATE_LIMIT_PER_MINUTE = 60

    def _parse_connection_string(self, connection_string: str) -> tuple[str, str] | None:
        parts = {}
        for segment in connection_string.split(";"):
            if "=" in segment:
                key, value = segment.split("=", 1)
                parts[key.strip().lower()] = value.strip()
        endpoint = parts.get("endpoint") or parts.get("endpointurl")
        access_key = parts.get("accesskey") or parts.get("sharedaccesskey")
        if endpoint and access_key:
            return endpoint, access_key
        return None

    def _get_credentials(self) -> tuple[str, str]:
        connection_string = resolve_secret(
            os.getenv("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING")
            or os.getenv("ACS_CONNECTION_STRING")
        )
        endpoint = resolve_secret(os.getenv("ACS_ENDPOINT"))
        access_key = resolve_secret(os.getenv("ACS_ACCESS_KEY"))
        if connection_string:
            parsed = self._parse_connection_string(connection_string)
            if parsed:
                return parsed
        if not endpoint:
            endpoint = DEFAULT_ACS_ENDPOINT
        if not access_key:
            raise ValueError("ACS_ACCESS_KEY or connection string is required")
        return endpoint, access_key

    def _build_client(self) -> HttpClient:
        if self._client:
            return self._client
        endpoint, access_key = self._get_credentials()
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        self._client = HttpClient(
            base_url=endpoint,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "api-key": access_key,
            },
            timeout=30.0,
            rate_limit_per_minute=self.RATE_LIMIT_PER_MINUTE,
            retry_config=retry_config,
            transport=self._transport,
        )
        return self._client

    def __init__(self, config: ConnectorConfig, **kwargs: Any) -> None:
        super().__init__(config, **kwargs)
