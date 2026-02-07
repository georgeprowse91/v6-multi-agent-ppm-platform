"""
Microsoft 365 Connector Implementation.

Supports:
- OAuth2 authentication via Microsoft Graph
- Workload-level data pulls for Teams, Exchange, SharePoint, Planner, OneDrive, Power BI, and Viva
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
from rest_connector import OAuth2RestConnector
from secrets import resolve_secret

DEFAULT_GRAPH_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


class M365Connector(OAuth2RestConnector):
    CONNECTOR_ID = "m365"
    CONNECTOR_NAME = "Microsoft 365"
    CONNECTOR_VERSION = "1.0.0"
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

    def read_workloads(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, dict[str, list[dict[str, Any]]]]:
        workloads = self._get_enabled_workloads()
        results: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for workload in workloads:
            workload_results: dict[str, list[dict[str, Any]]] = {}
            for resource_type in self.WORKLOAD_RESOURCE_MAP.get(workload, []):
                workload_results[resource_type] = self.read(
                    resource_type,
                    filters=filters,
                    limit=limit,
                    offset=offset,
                )
            results[workload] = workload_results
        return results

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
