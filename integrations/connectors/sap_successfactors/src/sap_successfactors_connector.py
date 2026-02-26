"""
SAP SuccessFactors Connector Implementation.

Supports:
- OAuth2 authentication
- Reading employee and job data
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


class SapSuccessFactorsConnector(OAuth2RestConnector):
    CONNECTOR_ID = "sap_successfactors"
    CONNECTOR_NAME = "SAP SuccessFactors"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.HRIS
    SUPPORTS_WRITE = False

    INSTANCE_URL_ENV = "SF_API_SERVER"
    CLIENT_ID_ENV = "SF_CLIENT_ID"
    CLIENT_SECRET_ENV = "SF_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "SF_REFRESH_TOKEN"
    TOKEN_URL_ENV = "SF_TOKEN_URL"
    DEFAULT_TOKEN_URL = "https://api.successfactors.com/oauth/token"
    SCOPES_ENV = "SF_SCOPES"
    KEYVAULT_URL_ENV = "SF_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "SF_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "SF_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "SF_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/odata/v2/User"
    AUTH_TEST_PARAMS = {"$top": 1}
    RESOURCE_PATHS = {
        "users": {"path": "/odata/v2/User", "items_path": "d.results"},
        "jobs": {"path": "/odata/v2/EmpJob", "items_path": "d.results"},
    }
    SCHEMA = {
        "users": {"userId": "string", "firstName": "string", "lastName": "string"},
        "jobs": {"userId": "string", "position": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
