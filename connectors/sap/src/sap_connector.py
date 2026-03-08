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
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig, ConnectorSearchResult  # noqa: E402
from connector_secrets import resolve_secret  # noqa: E402
from http_client import HttpClient  # noqa: E402
from mcp_client import MCPClient, MCPClientError  # noqa: E402
from rest_connector import BasicAuthRestConnector  # noqa: E402

try:
    from .mappers import map_from_mcp_response, map_to_mcp_params
except ImportError:
    import importlib.util as _ilu
    _mappers_spec = _ilu.spec_from_file_location(
        "sap_mappers", Path(__file__).with_name("mappers.py"),
    )
    _mappers_mod = _ilu.module_from_spec(_mappers_spec)
    _mappers_spec.loader.exec_module(_mappers_mod)
    map_from_mcp_response = _mappers_mod.map_from_mcp_response
    map_to_mcp_params = _mappers_mod.map_to_mcp_params

logger = logging.getLogger(__name__)


class SapConnector(BasicAuthRestConnector):
    CONNECTOR_ID = "sap"
    CONNECTOR_NAME = "SAP"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.ERP
    SUPPORTS_WRITE = True
    IDEMPOTENCY_FIELDS = ("ProjectID", "id", "external_id")
    CONFLICT_TIMESTAMP_FIELD = "LastChangedAt"

    INSTANCE_URL_ENV = "SAP_URL"
    USERNAME_ENV = "SAP_USERNAME"
    PASSWORD_ENV = "SAP_PASSWORD"
    AUTH_TEST_ENDPOINT = "/sap/opu/odata/sap/PROJECT_SRV/Projects"
    AUTH_TEST_PARAMS = {"$top": 1}
    RESOURCE_PATHS = {
        "projects": {"path": "/sap/opu/odata/sap/PROJECT_SRV/Projects", "items_path": "d.results", "write_path": "/sap/opu/odata/sap/PROJECT_SRV/Projects", "write_method": "POST"},
        "costs": {
            "path": "/sap/opu/odata/sap/PROJECT_SRV/ProjectCosts",
            "items_path": "d.results",
            "write_path": "/sap/opu/odata/sap/PROJECT_SRV/ProjectCosts",
            "write_method": "POST",
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
        params = map_to_mcp_params(
            "list",
            {
                "resource_type": resource_type,
                "filters": filters or {},
                "limit": limit,
                "offset": offset,
            },
        )
        try:
            client = self._build_mcp_client()
            payload = self._run_mcp(client.invoke_tool(tool_name, params))
            return map_from_mcp_response("list", payload)
        except (MCPClientError, ValueError) as exc:
            logger.warning(
                "MCP %s failed for SAP connector; falling back to REST. Error: %s",
                tool_key,
                exc,
            )
            return rest_call()

    def search(
        self,
        query: str,
        *,
        resource_types: list[str] | None = None,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[ConnectorSearchResult]:
        """Search SAP projects and costs using OData $filter."""
        if not query or not query.strip():
            return []
        if not self._authenticated and not self.authenticate():
            return []

        results: list[ConnectorSearchResult] = []
        types_to_search = resource_types or ["projects"]

        if "projects" in types_to_search:
            try:
                escaped = query.replace("'", "''")
                response = self._request(
                    "GET",
                    "/sap/opu/odata/sap/PROJECT_SRV/Projects",
                    params={
                        "$filter": f"substringof('{escaped}', Description) or substringof('{escaped}', ProjectID)",
                        "$top": limit,
                    },
                )
                data = response.json()
                items = data
                for key in "d.results".split("."):
                    if isinstance(items, dict):
                        items = items.get(key, {})
                if isinstance(items, list):
                    for record in items:
                        results.append(
                            ConnectorSearchResult(
                                id=str(record.get("ProjectID", "")),
                                title=record.get("Description") or str(record.get("ProjectID", "")),
                                snippet=f"SAP Project · {record.get('ProjectID', '')}",
                                source_system="sap",
                                resource_type="projects",
                                url=None,
                                score=0.9,
                                updated_at=record.get("LastChangedAt"),
                                metadata=record,
                            )
                        )
            except Exception:
                logger.warning("SAP search failed for query: %s; falling back to read-scan", query)
                return super().search(
                    query, resource_types=resource_types, limit=limit, filters=filters
                )

        return results[:limit]

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
            rest_call=lambda: BasicAuthRestConnector.read(self, resource_type, filters=filters, limit=limit, offset=offset),
        )
