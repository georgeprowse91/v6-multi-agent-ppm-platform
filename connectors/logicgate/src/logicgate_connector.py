"""
LogicGate Connector Implementation.

Supports:
- API key authentication
- Reading workflow records
- Writing records
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from rest_connector import ApiKeyRestConnector  # noqa: E402


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
