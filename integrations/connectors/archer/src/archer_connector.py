"""
RSA Archer Connector Implementation.

Supports:
- API key authentication
- Reading risk records
"""

from __future__ import annotations

import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import ApiKeyRestConnector


class ArcherConnector(ApiKeyRestConnector):
    CONNECTOR_ID = "archer"
    CONNECTOR_NAME = "RSA Archer"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.GRC
    SUPPORTS_WRITE = False

    API_KEY_ENV = "ARCHER_API_KEY"
    INSTANCE_URL_ENV = "ARCHER_URL"
    API_KEY_HEADER = "X-Archer-API-Key"
    AUTH_TEST_ENDPOINT = "/api/core/system/health"
    RESOURCE_PATHS = {
        "risks": {"path": "/api/core/content/records", "items_path": "value"},
    }
    SCHEMA = {
        "risks": {"id": "string", "title": "string", "status": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
