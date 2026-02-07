"""
LogicGate Connector Implementation.

Supports:
- API key authentication
- Reading workflow records
- Writing records
"""

from __future__ import annotations

import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import ApiKeyRestConnector


class LogicGateConnector(ApiKeyRestConnector):
    CONNECTOR_ID = "logicgate"
    CONNECTOR_NAME = "LogicGate"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.GRC
    SUPPORTS_WRITE = True

    API_KEY_ENV = "LOGICGATE_API_KEY"
    INSTANCE_URL_ENV = "LOGICGATE_API_URL"
    API_KEY_HEADER = "Authorization"
    API_KEY_PREFIX = "Bearer"
    AUTH_TEST_ENDPOINT = "/api/v1/workflows"
    RESOURCE_PATHS = {
        "workflows": {"path": "/api/v1/workflows", "items_path": "data"},
        "records": {"path": "/api/v1/records", "items_path": "data", "write_path": "/api/v1/records"},
    }
    SCHEMA = {
        "workflows": {"id": "string", "name": "string"},
        "records": {"id": "string", "status": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
