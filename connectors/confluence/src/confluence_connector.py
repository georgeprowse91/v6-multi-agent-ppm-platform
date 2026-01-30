"""
Confluence Connector Implementation.

Supports:
- Basic authentication (email + API token)
- Reading spaces and pages
- Writing pages
"""

from __future__ import annotations

import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import BasicAuthRestConnector


class ConfluenceConnector(BasicAuthRestConnector):
    CONNECTOR_ID = "confluence"
    CONNECTOR_NAME = "Confluence"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.DOC_MGMT
    SUPPORTS_WRITE = True

    INSTANCE_URL_ENV = "CONFLUENCE_URL"
    USERNAME_ENV = "CONFLUENCE_EMAIL"
    PASSWORD_ENV = "CONFLUENCE_API_TOKEN"
    AUTH_TEST_ENDPOINT = "/wiki/rest/api/space"
    AUTH_TEST_PARAMS = {"limit": 1}
    RESOURCE_PATHS = {
        "spaces": {"path": "/wiki/rest/api/space", "items_path": "results"},
        "pages": {
            "path": "/wiki/rest/api/content",
            "items_path": "results",
            "write_path": "/wiki/rest/api/content",
        },
    }
    SCHEMA = {
        "spaces": {"id": "string", "key": "string", "name": "string"},
        "pages": {"id": "string", "title": "string", "type": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
