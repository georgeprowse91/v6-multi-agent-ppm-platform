"""
Smartsheet Connector Implementation.

Supports:
- API token authentication
- Reading sheets
- Writing sheets
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import ApiKeyRestConnector
from secrets import resolve_secret

DEFAULT_SMARTSHEET_URL = "https://api.smartsheet.com/2.0"


class SmartsheetConnector(ApiKeyRestConnector):
    CONNECTOR_ID = "smartsheet"
    CONNECTOR_NAME = "Smartsheet"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.PM
    SUPPORTS_WRITE = True

    INSTANCE_URL_ENV = "SMARTSHEET_API_URL"
    API_KEY_ENV = "SMARTSHEET_API_TOKEN"
    API_KEY_HEADER = "Authorization"
    API_KEY_PREFIX = "Bearer"
    RATE_LIMIT_PER_MINUTE = 60

    AUTH_TEST_ENDPOINT = "/users/me"
    RESOURCE_PATHS = {
        "sheets": {
            "path": "/sheets",
            "items_path": "data",
            "write_path": "/sheets",
            "write_method": "POST",
        },
        "workspaces": {"path": "/workspaces", "items_path": "data"},
    }
    SCHEMA = {
        "sheets": {"id": "string", "name": "string"},
        "workspaces": {"id": "string", "name": "string"},
    }

    def _get_credentials(self) -> tuple[str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        if not instance_url:
            instance_url = DEFAULT_SMARTSHEET_URL
        api_token = resolve_secret(os.getenv(self.API_KEY_ENV))
        if not api_token:
            raise ValueError(f"{self.API_KEY_ENV} environment variable is required")
        return instance_url, api_token

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
