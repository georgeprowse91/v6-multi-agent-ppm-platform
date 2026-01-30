"""
ADP Connector Implementation.

Supports:
- OAuth2 authentication
- Reading worker and payroll data
"""

from __future__ import annotations

import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import OAuth2RestConnector


class AdpConnector(OAuth2RestConnector):
    CONNECTOR_ID = "adp"
    CONNECTOR_NAME = "ADP"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.HRIS
    SUPPORTS_WRITE = False

    INSTANCE_URL_ENV = "ADP_API_URL"
    CLIENT_ID_ENV = "ADP_CLIENT_ID"
    CLIENT_SECRET_ENV = "ADP_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "ADP_REFRESH_TOKEN"
    TOKEN_URL_ENV = "ADP_TOKEN_URL"
    DEFAULT_TOKEN_URL = "https://accounts.adp.com/auth/oauth/v2/token"
    SCOPES_ENV = "ADP_SCOPES"
    KEYVAULT_URL_ENV = "ADP_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "ADP_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "ADP_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "ADP_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/hr/v2/workers"
    AUTH_TEST_PARAMS = {"$top": 1}
    RESOURCE_PATHS = {
        "workers": {"path": "/hr/v2/workers", "items_path": "workers"},
        "payroll": {"path": "/payroll/v2/payroll-output", "items_path": "payrollOutputs"},
    }
    SCHEMA = {
        "workers": {"associateOID": "string", "name": "string"},
        "payroll": {"payrollRunId": "string", "grossPay": "number"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
