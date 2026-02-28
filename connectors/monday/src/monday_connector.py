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

_REPO_ROOT = Path(__file__).resolve().parents[4]
_COMMON_SRC = _REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from rest_connector import ApiKeyRestConnector  # noqa: E402


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
