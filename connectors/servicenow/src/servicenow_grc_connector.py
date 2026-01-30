"""
ServiceNow GRC Connector Implementation.

Supports:
- OAuth2 authentication
- Reading GRC profiles and risks
- Writing risks
"""

from __future__ import annotations

import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import OAuth2RestConnector


class ServiceNowGrcConnector(OAuth2RestConnector):
    CONNECTOR_ID = "servicenow_grc"
    CONNECTOR_NAME = "ServiceNow GRC"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.GRC
    SUPPORTS_WRITE = True

    INSTANCE_URL_ENV = "SERVICENOW_URL"
    CLIENT_ID_ENV = "SERVICENOW_CLIENT_ID"
    CLIENT_SECRET_ENV = "SERVICENOW_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "SERVICENOW_REFRESH_TOKEN"
    TOKEN_URL_ENV = "SERVICENOW_TOKEN_URL"
    DEFAULT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    SCOPES_ENV = "SERVICENOW_SCOPES"

    AUTH_TEST_ENDPOINT = "/api/now/table/sn_grc_profile"
    AUTH_TEST_PARAMS = {"sysparm_limit": 1}
    RESOURCE_PATHS = {
        "profiles": {"path": "/api/now/table/sn_grc_profile", "items_path": "result"},
        "risks": {
            "path": "/api/now/table/sn_risk",
            "items_path": "result",
            "write_path": "/api/now/table/sn_risk",
        },
    }
    SCHEMA = {
        "profiles": {"sys_id": "string", "name": "string"},
        "risks": {"sys_id": "string", "short_description": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
