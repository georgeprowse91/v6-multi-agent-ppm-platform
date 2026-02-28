"""MCP connector implementations for integration framework."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Iterable

import httpx

from connectors.mcp_client.auth import AuthConfig
from connectors.mcp_client.client import MCPClient
from connectors.mcp_client.errors import MCPToolNotFoundError

from .framework import BaseIntegrationConnector, ConnectorSettings, IntegrationConfig

logger = logging.getLogger(__name__)


class McpConnectorBase(BaseIntegrationConnector):
    """Base MCP connector with tool routing and REST fallback support."""

    system_name = "mcp"
    default_tool_map: Dict[str, str] = {}
    fallback_endpoints: Dict[str, str] = {}

    def __init__(
        self,
        config: IntegrationConfig,
        settings: ConnectorSettings | None = None,
        *,
        rest_connector: BaseIntegrationConnector | None = None,
        mcp_client: MCPClient | None = None,
    ) -> None:
        super().__init__(config, settings=settings)
        self._rest_connector = rest_connector
        self._mcp_client = mcp_client
        self._tool_map = {**self.default_tool_map, **(config.mcp_tool_map or {})}

    def authenticate(self) -> bool:
        return bool(self.config.mcp_server_url)

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        params = {"filters": filters or {}}
        try:
            result = self._invoke_tool("list_projects", params)
            return self._extract_records(result)
        except MCPToolNotFoundError:
            return self._fallback_list("projects")

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = self._invoke_tool("create_work_item", payload)
            return result if isinstance(result, dict) else {"result": result}
        except MCPToolNotFoundError:
            return self._fallback_create("work_items", payload)

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = self._invoke_tool("send_message", payload)
            return result if isinstance(result, dict) else {"result": result}
        except MCPToolNotFoundError:
            return self._fallback_create("messages", payload)

    def _build_mcp_client(self) -> MCPClient:
        if self._mcp_client:
            return self._mcp_client
        if not self.config.mcp_server_url:
            raise ValueError("MCP server URL is required")
        auth = AuthConfig(
            api_key=self.config.mcp_api_key,
            api_key_header=self.config.mcp_api_key_header or "X-API-Key",
            oauth_token=self.config.mcp_oauth_token,
            client_id=self.config.mcp_client_id,
            client_secret=self.config.mcp_client_secret,
            scope=self.config.mcp_scope,
        )
        self._mcp_client = MCPClient(
            mcp_server_id=self.config.mcp_server_id or self.config.system,
            mcp_server_url=self.config.mcp_server_url,
            auth=auth,
            tool_map=self._tool_map,
        )
        return self._mcp_client

    def _invoke_tool(self, tool_key: str, params: Dict[str, Any]) -> Any:
        tool_name = self._tool_map.get(tool_key)
        if not tool_name:
            raise MCPToolNotFoundError(f"Tool mapping missing for {tool_key}")
        client = self._build_mcp_client()
        return self._run_mcp(client.invoke_tool(tool_name, params))

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

    def _extract_records(self, payload: Any) -> list[Dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("records", "items", "values", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _fallback_list(self, key: str) -> list[Dict[str, Any]]:
        if not self._rest_connector:
            return []
        endpoint = self.fallback_endpoints.get(key)
        if not endpoint:
            return []
        try:
            response = self._rest_connector.fetch(endpoint)
        except httpx.HTTPError as exc:
            logger.warning(
                "REST fallback list failed",
                extra={"system": self.system_name, "endpoint": endpoint},
                exc_info=True,
            )
            return []
        return self._extract_records(response)

    def _fallback_create(self, key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._rest_connector:
            return {"status": "skipped", "reason": "no_rest_connector"}
        endpoint = self.fallback_endpoints.get(key)
        if not endpoint:
            return {"status": "skipped", "reason": "no_fallback_endpoint"}
        try:
            return self._rest_connector.post(endpoint, payload)
        except httpx.HTTPError as exc:
            logger.warning(
                "REST fallback create failed",
                extra={"system": self.system_name, "endpoint": endpoint},
                exc_info=True,
            )
            return {"status": "failed", "reason": str(exc)}

    def _merge_records(
        self,
        primary: Iterable[Dict[str, Any]],
        secondary: Iterable[Dict[str, Any]],
        *,
        key: str = "id",
    ) -> list[Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        for item in primary:
            item_id = item.get(key)
            if not item_id:
                continue
            merged[item_id] = dict(item)
        for item in secondary:
            item_id = item.get(key)
            if not item_id:
                continue
            merged.setdefault(item_id, {}).update(item)
        return list(merged.values())


class SlackMcpConnector(McpConnectorBase):
    system_name = "slack"
    default_tool_map = {
        "list_projects": "slack.listChannels",
        "send_message": "slack.postMessage",
        "create_work_item": "slack.createWorkItem",
        "list_users": "slack.listUsers",
    }
    fallback_endpoints = {"projects": "/conversations.list", "messages": "/chat.postMessage"}

    def list_users(self) -> list[Dict[str, Any]]:
        result = self._invoke_tool("list_users", {})
        return self._extract_records(result)


class TeamsMcpConnector(McpConnectorBase):
    system_name = "teams"
    default_tool_map = {
        "list_projects": "teams.listTeams",
        "send_message": "teams.postMessage",
        "create_work_item": "teams.createWorkItem",
        "list_channels": "teams.listChannels",
    }
    fallback_endpoints = {"projects": "/teams", "messages": "/teams/sendMessage"}

    def list_channels(self, team_id: str) -> list[Dict[str, Any]]:
        result = self._invoke_tool("list_channels", {"team_id": team_id})
        return self._extract_records(result)


class PlanviewMcpConnector(McpConnectorBase):
    system_name = "planview"
    default_tool_map = {
        "list_projects": "planview.listProjects",
        "create_work_item": "planview.createWorkItem",
    }
    fallback_endpoints = {
        "projects": "/api/v1/projects",
        "work_items": "/api/v1/work-items",
        "costs": "/api/v1/projects/costs",
    }

    def list_projects(
        self, filters: Dict[str, Any] | None = None, *, include_costs: bool = False
    ) -> list[Dict[str, Any]]:
        projects = super().list_projects(filters=filters)
        if include_costs:
            costs = self._fallback_list("costs")
            if costs:
                return self._merge_records(projects, costs, key="id")
        return projects


class ClarityMcpConnector(McpConnectorBase):
    system_name = "clarity"
    default_tool_map = {
        "list_projects": "clarity.listProjects",
        "create_work_item": "clarity.createWorkItem",
    }
    fallback_endpoints = {
        "projects": "/ppm/rest/v1/projects",
        "work_items": "/ppm/rest/v1/tasks",
        "costs": "/ppm/rest/v1/financials",
    }

    def list_projects(
        self, filters: Dict[str, Any] | None = None, *, include_costs: bool = False
    ) -> list[Dict[str, Any]]:
        projects = super().list_projects(filters=filters)
        if include_costs:
            costs = self._fallback_list("costs")
            if costs:
                return self._merge_records(projects, costs, key="id")
        return projects


class AsanaMcpConnector(McpConnectorBase):
    system_name = "asana"
    default_tool_map = {
        "list_projects": "asana.listProjects",
        "create_work_item": "asana.createTask",
        "send_message": "asana.addComment",
    }
    fallback_endpoints = {"projects": "/projects", "work_items": "/tasks"}

