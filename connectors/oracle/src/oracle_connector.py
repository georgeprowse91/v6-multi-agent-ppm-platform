"""
Oracle ERP Cloud Connector Implementation.

Supports:
- OAuth2 authentication
- Reading projects and invoices
"""

from __future__ import annotations

import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import OAuth2RestConnector

DEFAULT_TOKEN_URL = "https://login.oraclecloud.com/oauth2/v1/token"


class OracleConnector(OAuth2RestConnector):
    CONNECTOR_ID = "oracle"
    CONNECTOR_NAME = "Oracle ERP Cloud"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.ERP
    SUPPORTS_WRITE = False

    INSTANCE_URL_ENV = "ORACLE_URL"
    CLIENT_ID_ENV = "ORACLE_CLIENT_ID"
    CLIENT_SECRET_ENV = "ORACLE_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "ORACLE_REFRESH_TOKEN"
    TOKEN_URL_ENV = "ORACLE_TOKEN_URL"
    DEFAULT_TOKEN_URL = DEFAULT_TOKEN_URL
    SCOPES_ENV = "ORACLE_SCOPES"
    KEYVAULT_URL_ENV = "ORACLE_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "ORACLE_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "ORACLE_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "ORACLE_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/fscmRestApi/resources/latest/projects"
    AUTH_TEST_PARAMS = {"limit": 1}
    RESOURCE_PATHS = {
        "projects": {"path": "/fscmRestApi/resources/latest/projects", "items_path": "items"},
        "invoices": {"path": "/fscmRestApi/resources/latest/invoices", "items_path": "items"},
    }
    SCHEMA = {
        "projects": {"ProjectId": "string", "Name": "string"},
        "invoices": {"InvoiceId": "string", "Amount": "number"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
