"""
Microsoft 365 Connector Implementation.

Supports:
- OAuth2 authentication via Microsoft Graph
- Workload-level data pulls for Teams, Exchange, SharePoint, Planner, OneDrive, Power BI, and Viva
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from mcp_client import MCPClient, MCPClientError, MCPToolNotFoundError
from rest_connector import OAuth2RestConnector
from secrets import resolve_secret

DEFAULT_GRAPH_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

logger = logging.getLogger(__name__)


class M365Connector(OAuth2RestConnector):
    CONNECTOR_ID = "m365"
    CONNECTOR_NAME = "Microsoft 365"
    CONNECTOR_VERSION = "1.1.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = False

    INSTANCE_URL_ENV = "M365_API_URL"
    CLIENT_ID_ENV = "M365_CLIENT_ID"
    CLIENT_SECRET_ENV = "M365_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "M365_REFRESH_TOKEN"
    TOKEN_URL_ENV = "M365_TOKEN_URL"
    DEFAULT_TOKEN_URL = DEFAULT_TOKEN_URL
    SCOPES_ENV = "M365_SCOPES"
    KEYVAULT_URL_ENV = "M365_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "M365_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "M365_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "M365_CLIENT_ID_SECRET"
    TOOL_MAP_PATH = Path(__file__).resolve().parents[1] / "tool_map.yaml"

    AUTH_TEST_ENDPOINT = "/me"
    AUTH_TEST_PARAMS = {"$select": "id"}

    RESOURCE_PATHS = {
        "teams": {"path": "/me/joinedTeams", "items_path": "value"},
        "channels": {"path": "/teams/{team_id}/channels", "items_path": "value"},
        "messages": {
            "path": "/teams/{team_id}/channels/{channel_id}/messages",
            "items_path": "value",
        },
        "events": {"path": "/me/events", "items_path": "value"},
        "mail": {"path": "/me/messages", "items_path": "value"},
        "sites": {"path": "/sites", "items_path": "value"},
        "drives": {"path": "/me/drives", "items_path": "value"},
        "lists": {"path": "/sites/{site_id}/lists", "items_path": "value"},
        "planner_plans": {"path": "/me/planner/plans", "items_path": "value"},
        "planner_tasks": {"path": "/me/planner/tasks", "items_path": "value"},
        "drive_items": {"path": "/me/drive/root/children", "items_path": "value"},
        "powerbi_reports": {"path": "/reports", "items_path": "value"},
        "powerbi_dashboards": {"path": "/dashboards", "items_path": "value"},
        "viva_learning": {"path": "/employeeExperience/learningProviders", "items_path": "value"},
    }

    WORKLOAD_RESOURCE_MAP = {
        "teams": ["teams", "channels", "messages"],
        "exchange": ["events", "mail"],
        "sharepoint": ["sites", "drives", "lists"],
        "planner": ["planner_plans", "planner_tasks"],
        "onedrive": ["drive_items"],
        "power_bi": ["powerbi_reports", "powerbi_dashboards"],
        "viva": ["viva_learning"],
    }

    WORKLOAD_DATA_TABLE_TYPES = (
        "user_list",
        "last_activity",
        "subscription_data",
        "cost_data",
        "last_login",
    )

    MCP_SUPPORTED_RESOURCES = {"teams", "channels", "messages", "events", "mail", "drive_items"}

    SCHEMA = {
        "teams": {"id": "string", "displayName": "string"},
        "channels": {"id": "string", "displayName": "string"},
        "messages": {"id": "string", "body": "string"},
        "events": {"id": "string", "subject": "string"},
        "mail": {"id": "string", "subject": "string"},
        "sites": {"id": "string", "name": "string"},
        "drives": {"id": "string", "name": "string"},
        "lists": {"id": "string", "displayName": "string"},
        "planner_plans": {"id": "string", "title": "string"},
        "planner_tasks": {"id": "string", "title": "string"},
        "drive_items": {"id": "string", "name": "string"},
        "powerbi_reports": {"id": "string", "name": "string"},
        "powerbi_dashboards": {"id": "string", "displayName": "string"},
        "viva_learning": {"id": "string", "title": "string"},
    }

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        if not instance_url:
            instance_url = DEFAULT_GRAPH_URL
        client_id = resolve_secret(os.getenv(self.CLIENT_ID_ENV))
        client_secret = resolve_secret(os.getenv(self.CLIENT_SECRET_ENV))
        refresh_token = resolve_secret(os.getenv(self.REFRESH_TOKEN_ENV))
        if not client_id or not client_secret or not refresh_token:
            raise ValueError(
                f"{self.CLIENT_ID_ENV}, {self.CLIENT_SECRET_ENV}, and {self.REFRESH_TOKEN_ENV} are required"
            )
        return instance_url, client_id, client_secret, refresh_token

    def _get_enabled_workloads(self) -> list[str]:
        custom_fields = self.config.custom_fields or {}
        explicit = custom_fields.get("workloads")
        if isinstance(explicit, list) and explicit:
            return [workload for workload in explicit if workload in self.WORKLOAD_RESOURCE_MAP]
        enabled: list[str] = []
        for workload in self.WORKLOAD_RESOURCE_MAP:
            toggle_key = f"enable_{workload}"
            if toggle_key in custom_fields:
                if custom_fields.get(toggle_key):
                    enabled.append(workload)
            else:
                enabled.append(workload)
        return enabled

    def _should_use_mcp_for_resource(self, resource_type: str) -> bool:
        if resource_type not in self.MCP_SUPPORTED_RESOURCES:
            return False
        if not self.config.prefer_mcp:
            return False
        if not self.config.is_mcp_enabled_for(resource_type):
            return False
        if not self.config.mcp_server_url:
            return False
        if not (self.config.mcp_tool_map or {}).get(resource_type):
            return False
        return True

    def _build_mcp_client(self) -> MCPClient:
        if getattr(self, "_mcp_client", None):
            return self._mcp_client
        if not self.config.mcp_server_url:
            raise ValueError("M365 MCP server URL is required")
        self._mcp_client = MCPClient(
            mcp_server_id=self.config.mcp_server_id or self.CONNECTOR_ID,
            mcp_server_url=self.config.mcp_server_url,
            config=self.config,
        )
        return self._mcp_client

    def _load_tool_map(self) -> dict[str, Any]:
        if self._data_type_tool_map is not None:
            return self._data_type_tool_map
        path = self.TOOL_MAP_PATH
        if not path.exists():
            logger.warning("M365 tool map file not found at %s", path)
            self._data_type_tool_map = {}
            return self._data_type_tool_map
        try:
            payload = yaml.safe_load(path.read_text()) or {}
        except Exception as exc:
            logger.warning("Failed to load M365 tool map: %s", exc)
            self._data_type_tool_map = {}
            return self._data_type_tool_map
        self._data_type_tool_map = payload if isinstance(payload, dict) else {}
        return self._data_type_tool_map

    def _resolve_data_type_route(self, workload: str, data_type: str) -> dict[str, Any]:
        tool_map = self._load_tool_map()
        workloads = tool_map.get("workloads", {})
        if not isinstance(workloads, dict):
            return {}
        workload_map = workloads.get(workload, {})
        if not isinstance(workload_map, dict):
            return {}
        route = workload_map.get(data_type, {})
        return route if isinstance(route, dict) else {}

    def _should_use_mcp_for_data_type(self, workload: str, data_type: str) -> tuple[bool, str | None]:
        route = self._resolve_data_type_route(workload, data_type)
        tool_key = route.get("mcp_tool_key")
        if not tool_key:
            return False, None
        if not self.config.prefer_mcp:
            return False, tool_key
        if not self.config.is_mcp_enabled_for(tool_key):
            return False, tool_key
        if not self.config.mcp_server_url:
            return False, tool_key
        if not (self.config.mcp_tool_map or {}).get(tool_key):
            return False, tool_key
        return True, tool_key

    def _extract_mcp_records(self, resource_type: str, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            items_path = self.RESOURCE_PATHS.get(resource_type, {}).get("items_path")
            if items_path:
                current: Any = payload
                for key in items_path.split("."):
                    if not isinstance(current, dict):
                        current = None
                        break
                    current = current.get(key)
                if isinstance(current, list):
                    return current
            for key in ("records", "items", "values", "data", "value"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
            return [payload]
        return []

    def _extract_rest_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("value", "records", "items", "values", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
            return [payload]
        return []

    def _read_rest_endpoint(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        if not self._authenticated and not self.authenticate():
            raise RuntimeError("Failed to authenticate with connector")
        response = self._request("GET", endpoint, params=params or {})
        return self._extract_rest_records(response.json())

    def _read_via_mcp(
        self,
        resource_type: str,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        client = self._build_mcp_client()
        params = {
            "filters": filters or {},
            "limit": limit,
            "offset": offset,
        }
        payload = client.call_tool(resource_type, params)
        return self._extract_mcp_records(resource_type, payload)

    def read_data_type(
        self,
        workload: str,
        data_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        route = self._resolve_data_type_route(workload, data_type)
        params = {"limit": limit, "offset": offset}
        if filters:
            params.update(filters)
        use_mcp, tool_key = self._should_use_mcp_for_data_type(workload, data_type)
        if use_mcp and tool_key:
            try:
                payload = self._build_mcp_client().call_tool(tool_key, params)
                return self._extract_mcp_records(tool_key, payload)
            except MCPToolNotFoundError:
                logger.info(
                    "MCP tool mapping missing for %s/%s; falling back to Graph REST",
                    workload,
                    data_type,
                )
            except MCPClientError as exc:
                logger.warning(
                    "MCP request failed for %s/%s; falling back to Graph REST: %s",
                    workload,
                    data_type,
                    exc,
                )
        endpoint = route.get("rest_endpoint")
        if not endpoint:
            logger.warning("No REST endpoint mapping for %s/%s", workload, data_type)
            return []
        return self._read_rest_endpoint(endpoint, params)

    def read_data_table(
        self,
        workload: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, list[dict[str, Any]]]:
        table: dict[str, list[dict[str, Any]]] = {}
        for data_type in self.WORKLOAD_DATA_TABLE_TYPES:
            table[data_type] = self.read_data_type(
                workload,
                data_type,
                filters=filters,
                limit=limit,
                offset=offset,
            )
        return table

    def read_workloads(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, dict[str, list[dict[str, Any]]]]:
        working_filters = dict(filters or {})
        data_type = working_filters.pop("data_type", None)
        requested_workload = working_filters.pop("workload", None)
        workloads = self._get_enabled_workloads()
        if requested_workload:
            if isinstance(requested_workload, list):
                workloads = [item for item in requested_workload if item in workloads]
            elif isinstance(requested_workload, str) and requested_workload in workloads:
                workloads = [requested_workload]
        results: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for workload in workloads:
            workload_results: dict[str, list[dict[str, Any]]] = {}
            if data_type:
                if data_type == "data_table":
                    workload_results.update(
                        self.read_data_table(
                            workload,
                            filters=working_filters,
                            limit=limit,
                            offset=offset,
                        )
                    )
                else:
                    workload_results[data_type] = self.read_data_type(
                        workload,
                        data_type,
                        filters=working_filters,
                        limit=limit,
                        offset=offset,
                    )
            else:
                for resource_type in self.WORKLOAD_RESOURCE_MAP.get(workload, []):
                    if self._should_use_mcp_for_resource(resource_type):
                        try:
                            workload_results[resource_type] = self._read_via_mcp(
                                resource_type,
                                filters=working_filters,
                                limit=limit,
                                offset=offset,
                            )
                            continue
                        except MCPToolNotFoundError:
                            logger.info(
                                "MCP tool mapping missing for %s; falling back to Graph REST",
                                resource_type,
                            )
                        except MCPClientError as exc:
                            logger.warning(
                                "MCP request failed for %s; falling back to Graph REST: %s",
                                resource_type,
                                exc,
                            )
                    workload_results[resource_type] = self.read(
                        resource_type,
                        filters=working_filters,
                        limit=limit,
                        offset=offset,
                    )
            results[workload] = workload_results
        return results

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
        self._mcp_client: MCPClient | None = None
        self._data_type_tool_map: dict[str, Any] | None = None
