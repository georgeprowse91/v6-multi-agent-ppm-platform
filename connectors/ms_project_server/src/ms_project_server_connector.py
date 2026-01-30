"""
Microsoft Project Server Connector Implementation.

Supports:
- OAuth2 authentication
- Reading projects and tasks
- Writing tasks
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import OAuth2RestConnector
from secrets import resolve_secret


class MsProjectServerConnector(OAuth2RestConnector):
    CONNECTOR_ID = "ms_project_server"
    CONNECTOR_NAME = "Microsoft Project Server"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.PPM
    SUPPORTS_WRITE = True

    INSTANCE_URL_ENV = "MS_PROJECT_SITE_URL"
    CLIENT_ID_ENV = "MS_PROJECT_CLIENT_ID"
    CLIENT_SECRET_ENV = "MS_PROJECT_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "MS_PROJECT_REFRESH_TOKEN"
    TOKEN_URL_ENV = "MS_PROJECT_TOKEN_URL"
    DEFAULT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    SCOPES_ENV = "MS_PROJECT_SCOPES"

    AUTH_TEST_ENDPOINT = "/_api/ProjectServer/Projects"
    AUTH_TEST_PARAMS = {"$top": 1}
    RESOURCE_PATHS = {
        "projects": {"path": "/_api/ProjectServer/Projects", "items_path": "value"},
        "tasks": {
            "path": "/_api/ProjectServer/Projects('{project_id}')/Tasks",
            "items_path": "value",
            "write_path": "/_api/ProjectServer/Projects('{project_id}')/Tasks",
        },
    }
    SCHEMA = {
        "projects": {"Id": "string", "Name": "string"},
        "tasks": {"Id": "string", "Name": "string", "PercentComplete": "number"},
    }

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        if not instance_url:
            raise ValueError("MS_PROJECT_SITE_URL environment variable is required")
        client_id = resolve_secret(os.getenv(self.CLIENT_ID_ENV))
        client_secret = resolve_secret(os.getenv(self.CLIENT_SECRET_ENV))
        refresh_token = resolve_secret(os.getenv(self.REFRESH_TOKEN_ENV))
        if not client_id or not client_secret or not refresh_token:
            raise ValueError(
                f"{self.CLIENT_ID_ENV}, {self.CLIENT_SECRET_ENV}, and {self.REFRESH_TOKEN_ENV} are required"
            )
        tenant_id = resolve_secret(os.getenv("MS_PROJECT_TENANT_ID"))
        if tenant_id:
            self.DEFAULT_TOKEN_URL = (
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            )
        return instance_url, client_id, client_secret, refresh_token

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
