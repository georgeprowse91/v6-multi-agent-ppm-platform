"""
SharePoint Connector Implementation.

Supports:
- OAuth2 authentication
- Reading site lists and documents
- Writing documents (metadata updates)
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

DEFAULT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


class SharePointConnector(OAuth2RestConnector):
    CONNECTOR_ID = "sharepoint"
    CONNECTOR_NAME = "SharePoint"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.DOC_MGMT
    SUPPORTS_WRITE = True

    INSTANCE_URL_ENV = "SHAREPOINT_SITE_URL"
    CLIENT_ID_ENV = "SHAREPOINT_CLIENT_ID"
    CLIENT_SECRET_ENV = "SHAREPOINT_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "SHAREPOINT_REFRESH_TOKEN"
    TOKEN_URL_ENV = "SHAREPOINT_TOKEN_URL"
    DEFAULT_TOKEN_URL = DEFAULT_TOKEN_URL
    SCOPES_ENV = "SHAREPOINT_SCOPES"

    AUTH_TEST_ENDPOINT = "/_api/web"
    RESOURCE_PATHS = {
        "lists": {"path": "/_api/web/lists", "items_path": "value"},
        "documents": {
            "path": "/_api/web/lists/getbytitle('Documents')/items",
            "items_path": "value",
            "write_path": "/_api/web/lists/getbytitle('Documents')/items",
            "write_method": "POST",
        },
    }
    SCHEMA = {
        "lists": {"Id": "string", "Title": "string"},
        "documents": {"Id": "string", "Title": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
