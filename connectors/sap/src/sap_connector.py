"""
SAP Connector Implementation.

Supports:
- Basic authentication
- Reading projects and financial records
"""

from __future__ import annotations

import asyncio
import logging
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
from mcp_client import MCPClient, MCPClientError

logger = logging.getLogger(__name__)


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
        self._mcp_client: MCPClient | None = None
        self._mcp_tool_map = {
            "list_projects": "sap.listProjects",
            "list_costs": "sap.listCosts",
            **(config.mcp_tool_map or {}),
        }

    def _build_client(self) -> HttpClient:
        client = super()._build_client()
        sap_client = resolve_secret(os.getenv("SAP_CLIENT"))
        if sap_client:
            client.set_header("sap-client", sap_client)
        return client

    def _build_mcp_client(self) -> MCPClient:
        if self._mcp_client:
            return self._mcp_client
        if not self.config.mcp_server_url:
            raise ValueError("SAP MCP server URL is required")
        self._mcp_client = MCPClient(
            mcp_server_id=self.config.mcp_server_id or self.CONNECTOR_ID,
            mcp_server_url=self.config.mcp_server_url,
            config=self.config,
        )
        return self._mcp_client

    def _run_mcp(self, coroutine: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()

    def _should_use_mcp(self, tool_key: str) -> bool:
        if not self.config.prefer_mcp:
            return False
        if not self.config.mcp_server_url:
            return False
        if not self.config.is_mcp_enabled_for(tool_key):
            return False
        return True

    def _extract_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("records", "items", "values", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _list_records_via_mcp(
        self,
        *,
        resource_type: str,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        rest_call: Any,
    ) -> list[dict[str, Any]]:
        tool_key = f"list_{resource_type}"
        tool_name = self._mcp_tool_map.get(tool_key)
        if not self._should_use_mcp(tool_key):
            return rest_call()
        if not tool_name:
            logger.warning(
                "MCP tool mapping missing for %s; falling back to REST for SAP %s.",
                tool_key,
                resource_type,
            )
            return rest_call()
        params = {
            "resource_type": resource_type,
            "filters": filters or {},
            "limit": limit,
            "offset": offset,
        }
        try:
            client = self._build_mcp_client()
            payload = self._run_mcp(client.invoke_tool(tool_name, params))
            return self._extract_records(payload)
        except (MCPClientError, ValueError) as exc:
            logger.warning(
                "MCP %s failed for SAP connector; falling back to REST. Error: %s",
                tool_key,
                exc,
            )
            return rest_call()

    def read(
        self,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return self._list_records_via_mcp(
            resource_type=resource_type,
            filters=filters,
            limit=limit,
            offset=offset,
            rest_call=lambda: super().read(resource_type, filters=filters, limit=limit, offset=offset),
        )
