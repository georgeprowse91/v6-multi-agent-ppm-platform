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
from operation_router import OperationRouter
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
        self._operation_router = OperationRouter(config)

    def _build_client(self) -> HttpClient:
        client = super()._build_client()
        sap_client = resolve_secret(os.getenv("SAP_CLIENT"))
        if sap_client:
            client.set_header("sap-client", sap_client)
        return client

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
