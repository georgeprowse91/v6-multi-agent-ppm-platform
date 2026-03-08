"""
Azure Notification Hubs Connector Implementation.

Supports:
- SAS token authentication
- Sending push notifications
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
import urllib.parse
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from connector_secrets import resolve_secret  # noqa: E402
from http_client import HttpClient, RetryConfig  # noqa: E402
from rest_connector import RestConnector  # noqa: E402


class NotificationHubsConnector(RestConnector):
    CONNECTOR_ID = "notification_hubs"
    CONNECTOR_NAME = "Azure Notification Hubs"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = True

    AUTH_TEST_ENDPOINT = "/messages"
    RESOURCE_PATHS = {
        "notifications": {
            "path": "/messages",
            "write_path": "/messages",
            "write_method": "POST",
        }
    }
    SCHEMA = {"notifications": {"status": "string"}}
    RATE_LIMIT_PER_MINUTE = 60

    def _get_credentials(self) -> tuple[str, str, str]:
        namespace = resolve_secret(os.getenv("AZURE_NOTIFICATION_HUBS_NAMESPACE"))
        hub_name = resolve_secret(os.getenv("AZURE_NOTIFICATION_HUBS_NAME"))
        sas_key_name = resolve_secret(os.getenv("AZURE_NOTIFICATION_HUBS_SAS_KEY_NAME"))
        sas_key = resolve_secret(os.getenv("AZURE_NOTIFICATION_HUBS_SAS_KEY"))
        if not namespace or not hub_name or not sas_key_name or not sas_key:
            raise ValueError("Azure Notification Hubs configuration is required")
        base_url = f"https://{namespace}.servicebus.windows.net/{hub_name}"
        return base_url, sas_key_name, sas_key

    def _build_sas_token(self, uri: str, key_name: str, key: str) -> str:
        expiry = int(time.time() + 3600)
        encoded_uri = urllib.parse.quote_plus(uri)
        sign_key = f"{encoded_uri}\n{expiry}".encode()
        signature = base64.b64encode(
            hmac.new(base64.b64decode(key), sign_key, hashlib.sha256).digest()
        ).decode()
        return (
            f"SharedAccessSignature sr={encoded_uri}&sig={urllib.parse.quote_plus(signature)}"
            f"&se={expiry}&skn={key_name}"
        )

    def _build_client(self) -> HttpClient:
        if self._client:
            return self._client
        base_url, sas_key_name, sas_key = self._get_credentials()
        token = self._build_sas_token(base_url, sas_key_name, sas_key)
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        self._client = HttpClient(
            base_url=base_url,
            headers={
                "Accept": "application/json",
                "Authorization": token,
                "Content-Type": "application/json",
                "ServiceBusNotification-Format": "gcm",
            },
            timeout=30.0,
            rate_limit_per_minute=self.RATE_LIMIT_PER_MINUTE,
            retry_config=retry_config,
            transport=self._transport,
        )
        return self._client

    def __init__(self, config: ConnectorConfig, **kwargs: Any) -> None:
        super().__init__(config, **kwargs)
