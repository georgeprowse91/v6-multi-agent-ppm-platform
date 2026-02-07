"""
Workday Connector Implementation.

Supports:
- OAuth2 authentication
- Reading worker and position data
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from operation_router import OperationRouter
from rest_connector import OAuth2RestConnector

DEFAULT_TOKEN_URL = "https://wd3-impl-services1.workday.com/ccx/oauth2/token"


class WorkdayConnector(OAuth2RestConnector):
    CONNECTOR_ID = "workday"
    CONNECTOR_NAME = "Workday"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.HRIS
    SUPPORTS_WRITE = False

    INSTANCE_URL_ENV = "WORKDAY_API_URL"
    CLIENT_ID_ENV = "WORKDAY_CLIENT_ID"
    CLIENT_SECRET_ENV = "WORKDAY_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "WORKDAY_REFRESH_TOKEN"
    TOKEN_URL_ENV = "WORKDAY_TOKEN_URL"
    DEFAULT_TOKEN_URL = DEFAULT_TOKEN_URL
    SCOPES_ENV = "WORKDAY_SCOPES"
    KEYVAULT_URL_ENV = "WORKDAY_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "WORKDAY_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "WORKDAY_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "WORKDAY_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/ccx/api/v1/workers"
    AUTH_TEST_PARAMS = {"limit": 1}
    RESOURCE_PATHS = {
        "workers": {"path": "/ccx/api/v1/workers", "items_path": "data"},
        "positions": {"path": "/ccx/api/v1/positions", "items_path": "data"},
    }
    SCHEMA = {
        "workers": {"id": "string", "name": "string", "status": "string"},
        "positions": {"id": "string", "title": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
        self._operation_router = OperationRouter(config)

    def read(
        self,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        router = self._operation_router

        def rest_call() -> list[dict[str, Any]]:
            return super().read(resource_type, filters=filters, limit=limit, offset=offset)

        def mcp_call() -> list[dict[str, Any]]:
            client = router.build_mcp_client()
            params = {
                "resource_type": resource_type,
                "filters": filters or {},
                "limit": limit,
                "offset": offset,
            }
            payload = router.run_mcp(client.list_records(params))
            return router.extract_records(payload)

        return router.run("read", mcp_call=mcp_call, rest_call=rest_call)
