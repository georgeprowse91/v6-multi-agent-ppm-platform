"""
Google Drive Connector Implementation.

Supports:
- OAuth2 authentication
- Reading files and folders
- Writing metadata updates
"""

from __future__ import annotations

import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import OAuth2RestConnector

DEFAULT_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleDriveConnector(OAuth2RestConnector):
    CONNECTOR_ID = "google_drive"
    CONNECTOR_NAME = "Google Drive"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.DOC_MGMT
    SUPPORTS_WRITE = True

    INSTANCE_URL_ENV = "GOOGLE_DRIVE_BASE_URL"
    CLIENT_ID_ENV = "GOOGLE_CLIENT_ID"
    CLIENT_SECRET_ENV = "GOOGLE_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "GOOGLE_REFRESH_TOKEN"
    TOKEN_URL_ENV = "GOOGLE_TOKEN_URL"
    DEFAULT_TOKEN_URL = DEFAULT_TOKEN_URL
    SCOPES_ENV = "GOOGLE_SCOPES"

    AUTH_TEST_ENDPOINT = "/drive/v3/files"
    AUTH_TEST_PARAMS = {"pageSize": 1}
    RESOURCE_PATHS = {
        "files": {
            "path": "/drive/v3/files",
            "items_path": "files",
            "write_path": "/drive/v3/files",
            "write_method": "POST",
        },
        "folders": {"path": "/drive/v3/files", "items_path": "files"},
    }
    SCHEMA = {
        "files": {"id": "string", "name": "string", "mimeType": "string"},
        "folders": {"id": "string", "name": "string", "mimeType": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
