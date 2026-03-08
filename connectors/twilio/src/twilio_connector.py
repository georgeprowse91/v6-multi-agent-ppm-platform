"""
Twilio Connector Implementation.

Supports:
- Basic authentication
- Reading SMS messages
- Sending SMS messages
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from connector_secrets import resolve_secret  # noqa: E402
from http_client import HttpClient, RetryConfig  # noqa: E402
from rest_connector import RestConnector  # noqa: E402

DEFAULT_TWILIO_URL = "https://api.twilio.com/2010-04-01"


class TwilioConnector(RestConnector):
    CONNECTOR_ID = "twilio"
    CONNECTOR_NAME = "Twilio"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = True

    AUTH_TEST_ENDPOINT = "/Messages.json"
    RESOURCE_PATHS = {
        "messages": {
            "path": "/Messages.json",
            "items_path": "messages",
            "write_path": "/Messages.json",
            "write_method": "POST",
        }
    }
    SCHEMA = {"messages": {"sid": "string", "status": "string"}}
    RATE_LIMIT_PER_MINUTE = 60

    def _get_credentials(self) -> tuple[str, str, str]:
        base_url = resolve_secret(os.getenv("TWILIO_API_URL")) or DEFAULT_TWILIO_URL
        account_sid = resolve_secret(os.getenv("TWILIO_ACCOUNT_SID"))
        auth_token = resolve_secret(os.getenv("TWILIO_AUTH_TOKEN"))
        if not account_sid or not auth_token:
            raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are required")
        return base_url, account_sid, auth_token

    def _build_client(self) -> HttpClient:
        if self._client:
            return self._client
        base_url, account_sid, auth_token = self._get_credentials()
        auth_bytes = f"{account_sid}:{auth_token}".encode()
        auth_header = base64.b64encode(auth_bytes).decode("utf-8")
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        self._client = HttpClient(
            base_url=f"{base_url}/Accounts/{account_sid}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {auth_header}",
            },
            timeout=30.0,
            rate_limit_per_minute=self.RATE_LIMIT_PER_MINUTE,
            retry_config=retry_config,
            transport=self._transport,
        )
        return self._client

    def write(self, resource_type: str, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for payload in data:
            payload.setdefault("To", payload.get("to"))
            payload.setdefault("From", payload.get("from"))
            payload.setdefault("Body", payload.get("body"))
        return super().write(resource_type, data)

    def __init__(self, config: ConnectorConfig, **kwargs: Any) -> None:
        super().__init__(config, **kwargs)
