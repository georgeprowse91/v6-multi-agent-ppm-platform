"""
SAP Connector Implementation.

Supports:
- Basic authentication
- Reading projects and financial records
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
from http_client import HttpClient, RetryConfig
from rest_connector import BasicAuthRestConnector
from secrets import resolve_secret


class SapConnector(BasicAuthRestConnector):
    CONNECTOR_ID = "sap"
    CONNECTOR_NAME = "SAP"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.ERP
    SUPPORTS_WRITE = False

    INSTANCE_URL_ENV = "SAP_URL"
    USERNAME_ENV = "SAP_USERNAME"
    PASSWORD_ENV = "SAP_PASSWORD"
    AUTH_TEST_ENDPOINT = "/sap/opu/odata/sap/PROJECT_SRV/Projects"
    AUTH_TEST_PARAMS = {"$top": 1}
    RESOURCE_PATHS = {
        "projects": {"path": "/sap/opu/odata/sap/PROJECT_SRV/Projects", "items_path": "d.results"},
        "costs": {
            "path": "/sap/opu/odata/sap/PROJECT_SRV/ProjectCosts",
            "items_path": "d.results",
        },
    }
    SCHEMA = {
        "projects": {"ProjectID": "string", "Description": "string"},
        "costs": {"ProjectID": "string", "Amount": "number", "Currency": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
        self._client_id: str | None = None

    def _build_client(self) -> HttpClient:
        client = super()._build_client()
        sap_client = resolve_secret(os.getenv("SAP_CLIENT"))
        if sap_client:
            client.set_header("sap-client", sap_client)
        return client
