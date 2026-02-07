"""
Monday.com Connector Implementation.

Supports:
- API token authentication
- Reading boards and items
- Writing items
"""

from __future__ import annotations

import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import ApiKeyRestConnector


class MondayConnector(ApiKeyRestConnector):
    CONNECTOR_ID = "monday"
    CONNECTOR_NAME = "Monday.com"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.PM
    SUPPORTS_WRITE = True

    API_KEY_ENV = "MONDAY_API_TOKEN"
    INSTANCE_URL_ENV = "MONDAY_INSTANCE_URL"
    API_KEY_HEADER = "Authorization"
    API_KEY_PREFIX = "Bearer"
    AUTH_TEST_ENDPOINT = "/v2/boards"
    AUTH_TEST_PARAMS = {"limit": 1}
    RESOURCE_PATHS = {
        "boards": {"path": "/v2/boards", "items_path": "data.boards"},
        "items": {
            "path": "/v2/items",
            "items_path": "data.items",
            "write_path": "/v2/items",
            "write_method": "POST",
        },
    }
    SCHEMA = {
        "boards": {"id": "string", "name": "string"},
        "items": {"id": "string", "name": "string", "status": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
