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

_REPO_ROOT = Path(__file__).resolve().parents[4]
_COMMON_SRC = _REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from rest_connector import OAuth2RestConnector  # noqa: E402

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
    KEYVAULT_URL_ENV = "SHAREPOINT_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "SHAREPOINT_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "SHAREPOINT_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "SHAREPOINT_CLIENT_ID_SECRET"

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
