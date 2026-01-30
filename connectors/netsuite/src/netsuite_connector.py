"""
NetSuite Connector Implementation.

Supports:
- OAuth2 authentication
- Reading projects and customers
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from http_client import HttpClient
from rest_connector import OAuth2RestConnector
from secrets import resolve_secret

DEFAULT_TOKEN_URL = "https://accounts.netsuite.com/services/oauth2/v1/token"


class NetSuiteConnector(OAuth2RestConnector):
    CONNECTOR_ID = "netsuite"
    CONNECTOR_NAME = "NetSuite"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.ERP
    SUPPORTS_WRITE = False

    INSTANCE_URL_ENV = "NETSUITE_REST_URL"
    CLIENT_ID_ENV = "NETSUITE_CONSUMER_KEY"
    CLIENT_SECRET_ENV = "NETSUITE_CONSUMER_SECRET"
    REFRESH_TOKEN_ENV = "NETSUITE_REFRESH_TOKEN"
    TOKEN_URL_ENV = "NETSUITE_TOKEN_URL"
    DEFAULT_TOKEN_URL = DEFAULT_TOKEN_URL
    SCOPES_ENV = "NETSUITE_SCOPES"
    KEYVAULT_URL_ENV = "NETSUITE_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "NETSUITE_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "NETSUITE_CONSUMER_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "NETSUITE_CONSUMER_KEY_SECRET"

    AUTH_TEST_ENDPOINT = "/services/rest/record/v1/project"
    AUTH_TEST_PARAMS = {"limit": 1}
    RESOURCE_PATHS = {
        "projects": {"path": "/services/rest/record/v1/project", "items_path": "items"},
        "customers": {"path": "/services/rest/record/v1/customer", "items_path": "items"},
    }
    SCHEMA = {
        "projects": {"id": "string", "name": "string"},
        "customers": {"id": "string", "companyName": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
        self._account_id: str | None = None

    def _build_client(self) -> HttpClient:
        client = super()._build_client()
        account_id = resolve_secret(os.getenv("NETSUITE_ACCOUNT_ID"))
        if account_id:
            client.set_header("X-NetSuite-Account", account_id)
        return client
