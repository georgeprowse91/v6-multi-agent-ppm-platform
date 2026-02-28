"""
RSA Archer Connector Implementation.

Supports:
- API key authentication
- Reading risk records
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_COMMON_SRC = _REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from rest_connector import ApiKeyRestConnector  # noqa: E402


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
