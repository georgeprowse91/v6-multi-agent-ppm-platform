"""
Google Drive Connector Implementation.

Supports:
- OAuth2 authentication
- Reading files and folders
- Writing metadata updates
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from rest_connector import OAuth2RestConnector  # noqa: E402

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
    KEYVAULT_URL_ENV = "GOOGLE_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "GOOGLE_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "GOOGLE_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "GOOGLE_CLIENT_ID_SECRET"

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
