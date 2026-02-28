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

_REPO_ROOT = Path(__file__).resolve().parents[4]
_COMMON_SRC = _REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from rest_connector import OAuth2RestConnector  # noqa: E402


class ServiceNowGrcConnector(OAuth2RestConnector):
    CONNECTOR_ID = "servicenow_grc"
    CONNECTOR_NAME = "ServiceNow GRC"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.GRC
    SUPPORTS_WRITE = True
    IDEMPOTENCY_FIELDS = ("sys_id", "number", "id")
    CONFLICT_TIMESTAMP_FIELD = "sys_updated_on"

    INSTANCE_URL_ENV = "SERVICENOW_URL"
    CLIENT_ID_ENV = "SERVICENOW_CLIENT_ID"
    CLIENT_SECRET_ENV = "SERVICENOW_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "SERVICENOW_REFRESH_TOKEN"
    TOKEN_URL_ENV = "SERVICENOW_TOKEN_URL"
    DEFAULT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    SCOPES_ENV = "SERVICENOW_SCOPES"
    KEYVAULT_URL_ENV = "SERVICENOW_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "SERVICENOW_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "SERVICENOW_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "SERVICENOW_CLIENT_ID_SECRET"

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
