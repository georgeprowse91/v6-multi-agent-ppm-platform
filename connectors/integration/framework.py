"""Connector integration framework for external systems."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from runtime_flags import demo_mode_enabled


class IntegrationAuthType(str, Enum):
    API_KEY = "api_key"
    OAUTH = "oauth"
    BASIC = "basic"
    NONE = "none"


class ConnectorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CONNECTOR_", env_file=".env")

    timeout_seconds: int = 10
    retry_attempts: int = 2


@dataclass
class IntegrationConfig:
    system: str
    base_url: str
    auth_type: IntegrationAuthType = IntegrationAuthType.NONE
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    scopes: list[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    mcp_server_url: Optional[str] = None
    mcp_server_id: Optional[str] = None
    mcp_client_id: Optional[str] = None
    mcp_client_secret: Optional[str] = None
    mcp_scope: Optional[str] = None
    mcp_scopes: list[str] = field(default_factory=list)
    mcp_api_key: Optional[str] = None
    mcp_api_key_header: Optional[str] = None
    mcp_oauth_token: Optional[str] = None
    mcp_tool_map: Dict[str, str] = field(default_factory=dict)
    prefer_mcp: bool = False


class BaseIntegrationConnector:
    """Base connector to authenticate, fetch, and post data."""

    system_name: str = "base"

    def __init__(self, config: IntegrationConfig, settings: Optional[ConnectorSettings] = None) -> None:
        self.config = config
        self.settings = settings or ConnectorSettings()

    def authenticate(self) -> bool:
        if self.config.auth_type == IntegrationAuthType.NONE:
            return True
        if self.config.auth_type == IntegrationAuthType.API_KEY:
            return bool(self.config.api_key)
        if self.config.auth_type == IntegrationAuthType.BASIC:
            return bool(self.config.username and self.config.password)
        if self.config.auth_type == IntegrationAuthType.OAUTH:
            return bool(self.config.client_id and self.config.client_secret)
        return False

    def headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.config.auth_type == IntegrationAuthType.API_KEY and self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if self.config.auth_type == IntegrationAuthType.BASIC and self.config.username:
            headers["X-Auth-User"] = self.config.username
        if self.config.auth_type == IntegrationAuthType.OAUTH and self.config.client_id:
            headers["X-Client-Id"] = self.config.client_id
        return headers

    def fetch(self, endpoint: str) -> Dict[str, Any]:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("httpx is required for connector fetch") from exc

        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        response = httpx.get(
            url,
            headers=self.headers(),
            timeout=self.settings.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("httpx is required for connector post") from exc

        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        response = httpx.post(
            url,
            headers=self.headers(),
            json=payload,
            timeout=self.settings.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def health_check(self) -> bool:
        try:
            return self.authenticate()
        except (RuntimeError, ValueError) as exc:
            logger.warning(
                "Connector health check failed",
                extra={"system": self.system_name, "error": str(exc)},
                exc_info=True,
            )
            return False

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        raise NotImplementedError

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class ConnectorRegistry:
    """Registry for external connectors."""

    def __init__(self) -> None:
        self._registry: Dict[str, Dict[str, Type[BaseIntegrationConnector]]] = {}

    def register(
        self,
        system: str,
        connector: Type[BaseIntegrationConnector],
        *,
        variant: str = "rest",
    ) -> None:
        self._registry.setdefault(system, {})[variant] = connector

    def create(
        self, system: str, config: IntegrationConfig, settings: Optional[ConnectorSettings] = None
    ) -> BaseIntegrationConnector:
        connector_cls = self._registry.get(system, {})
        if not connector_cls:
            raise ValueError(f"Unknown connector system: {system}")
        prefer_mcp = bool(config.prefer_mcp and config.mcp_server_url)
        if prefer_mcp and "mcp" in connector_cls:
            rest_connector = None
            if "rest" in connector_cls:
                rest_connector = connector_cls["rest"](config, settings=settings)
            return connector_cls["mcp"](config, settings=settings, rest_connector=rest_connector)
        if "rest" in connector_cls:
            return connector_cls["rest"](config, settings=settings)
        if "mcp" in connector_cls:
            return connector_cls["mcp"](config, settings=settings)
        raise ValueError(f"No connector variants registered for {system}")

    def list_systems(self) -> list[str]:
        return sorted(self._registry.keys())


class PlanviewConnector(BaseIntegrationConnector):
    system_name = "planview"

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        params = "&".join(f"{k}={v}" for k, v in (filters or {}).items())
        endpoint = f"api/v3/projects?{params}" if params else "api/v3/projects"
        data = self.fetch(endpoint)
        items = data.get("items") or data.get("data") or data.get("value") or []
        return items if isinstance(items, list) else [data]

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.post("api/v3/workItems", payload)

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("Planview does not support direct messaging")


class ClarityConnector(BaseIntegrationConnector):
    system_name = "clarity"

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        params = "&".join(f"{k}={v}" for k, v in (filters or {}).items())
        endpoint = f"ppm/rest/api/projects?{params}" if params else "ppm/rest/api/projects"
        data = self.fetch(endpoint)
        items = data.get("items") or data.get("data") or data.get("_items") or []
        return items if isinstance(items, list) else [data]

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.post("ppm/rest/api/tasks", payload)

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("Clarity does not support direct messaging")


class JiraConnector(BaseIntegrationConnector):
    system_name = "jira"

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        data = self.fetch("rest/api/3/project")
        return data if isinstance(data, list) else data.get("values", [data])

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        fields = payload.get("fields", payload)
        return self.post("rest/api/3/issue", {"fields": fields})

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        issue_key = payload.get("issue_key") or payload.get("issueKey", "")
        body = payload.get("body") or payload.get("message") or payload.get("text", "")
        return self.post(
            f"rest/api/3/issue/{issue_key}/comment",
            {"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": body}]}]}},
        )


class AzureDevOpsConnector(BaseIntegrationConnector):
    system_name = "azure_devops"

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        data = self.fetch("_apis/projects?api-version=7.0")
        return data.get("value", [])

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        project = payload.get("project", "_default")
        work_item_type = payload.get("type", "Task")
        fields = [
            {"op": "add", "path": f"/fields/{k}", "value": v}
            for k, v in payload.items()
            if k not in {"project", "type"}
        ]
        return self.post(
            f"{project}/_apis/wit/workitems/${work_item_type}?api-version=7.0",
            fields,
        )

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("Azure DevOps does not support direct messaging via this connector")


class SmartsheetConnector(BaseIntegrationConnector):
    system_name = "smartsheet"

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        data = self.fetch("2.0/sheets")
        return data.get("data", [])

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sheet_id = payload.get("sheet_id") or payload.get("sheetId", "")
        rows = payload.get("rows", [payload])
        return self.post(f"2.0/sheets/{sheet_id}/rows", rows)

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sheet_id = payload.get("sheet_id") or payload.get("sheetId", "")
        comment = payload.get("text") or payload.get("body") or payload.get("message", "")
        return self.post(f"2.0/sheets/{sheet_id}/discussions", {"comment": {"text": comment}})


class OutlookConnector(BaseIntegrationConnector):
    system_name = "outlook"

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        data = self.fetch("v1.0/me/todo/lists")
        return data.get("value", [])

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        list_id = payload.get("list_id") or payload.get("listId", "tasks")
        return self.post(f"v1.0/me/todo/lists/{list_id}/tasks", payload)

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        to_recipients = [
            {"emailAddress": {"address": addr}}
            for addr in ([payload["to"]] if isinstance(payload.get("to"), str) else payload.get("to", []))
        ]
        message = {
            "subject": payload.get("subject", ""),
            "body": {"contentType": "Text", "content": payload.get("body") or payload.get("message", "")},
            "toRecipients": to_recipients,
        }
        return self.post("v1.0/me/sendMail", {"message": message})


class GoogleCalendarConnector(BaseIntegrationConnector):
    system_name = "google_calendar"

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        data = self.fetch("calendar/v3/users/me/calendarList")
        return data.get("items", [])

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        calendar_id = payload.get("calendar_id") or payload.get("calendarId", "primary")
        return self.post(f"calendar/v3/calendars/{calendar_id}/events", payload)

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("Google Calendar does not support direct messaging")


class ServiceNowConnector(BaseIntegrationConnector):
    system_name = "servicenow"

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        params = "&".join(f"sysparm_query={k}={v}" for k, v in (filters or {}).items())
        endpoint = f"api/now/table/project_project?{params}" if params else "api/now/table/project_project"
        data = self.fetch(endpoint)
        return data.get("result", [])

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.post("api/now/table/pm_task", payload)

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("ServiceNow does not support direct messaging via this connector")


class AzureCommunicationConnector(BaseIntegrationConnector):
    system_name = "azure_communication"

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        raise ValueError("Azure Communication Services does not support project listing")

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("Azure Communication Services does not support work item creation")

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        channel = payload.get("channel", "email")
        if channel == "sms":
            return self.post("sms", {
                "from": payload.get("from", ""),
                "smsRecipients": [{"to": addr} for addr in ([payload["to"]] if isinstance(payload.get("to"), str) else payload.get("to", []))],
                "message": payload.get("message") or payload.get("body", ""),
            })
        return self.post("emails:send?api-version=2023-03-31", {
            "senderAddress": payload.get("from", ""),
            "recipients": {"to": [{"address": addr} for addr in ([payload["to"]] if isinstance(payload.get("to"), str) else payload.get("to", []))]},
            "content": {
                "subject": payload.get("subject", ""),
                "plainText": payload.get("message") or payload.get("body", ""),
            },
        })


class MockIntegrationConnector(BaseIntegrationConnector):
    """Simple mock connector that returns deterministic demo responses."""

    system_name = "mock"

    def list_projects(self, filters: Dict[str, Any] | None = None) -> list[Dict[str, Any]]:
        return [
            {
                "id": "demo-project-1",
                "name": "Demo Project",
                "system": self.config.system,
                "filters": filters or {},
            }
        ]

    def create_work_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "system": self.config.system, "payload": payload, "persisted": False}

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "system": self.config.system, "payload": payload, "persisted": False}


def default_registry() -> ConnectorRegistry:
    registry = ConnectorRegistry()
    from connectors.integration.mcp_connectors import (
        AsanaMcpConnector,
        ClarityMcpConnector,
        PlanviewMcpConnector,
        SlackMcpConnector,
        TeamsMcpConnector,
    )

    registry.register(PlanviewConnector.system_name, PlanviewConnector, variant="rest")
    registry.register(PlanviewMcpConnector.system_name, PlanviewMcpConnector, variant="mcp")
    registry.register(ClarityConnector.system_name, ClarityConnector, variant="rest")
    registry.register(ClarityMcpConnector.system_name, ClarityMcpConnector, variant="mcp")
    registry.register(JiraConnector.system_name, JiraConnector, variant="rest")
    registry.register(AzureDevOpsConnector.system_name, AzureDevOpsConnector, variant="rest")
    registry.register(SmartsheetConnector.system_name, SmartsheetConnector, variant="rest")
    registry.register(OutlookConnector.system_name, OutlookConnector, variant="rest")
    registry.register(GoogleCalendarConnector.system_name, GoogleCalendarConnector, variant="rest")
    registry.register(ServiceNowConnector.system_name, ServiceNowConnector, variant="rest")
    registry.register(AzureCommunicationConnector.system_name, AzureCommunicationConnector, variant="rest")
    registry.register(SlackMcpConnector.system_name, SlackMcpConnector, variant="mcp")
    registry.register(TeamsMcpConnector.system_name, TeamsMcpConnector, variant="mcp")
    registry.register(AsanaMcpConnector.system_name, AsanaMcpConnector, variant="mcp")

    if demo_mode_enabled():
        for system in ("jira", "workday", "teams", "sap", "servicenow", "azure_devops", "planview", "clarity"):
            registry.register(system, MockIntegrationConnector, variant="rest")

    return registry


__all__ = [
    "IntegrationAuthType",
    "IntegrationConfig",
    "ConnectorSettings",
    "BaseIntegrationConnector",
    "ConnectorRegistry",
    "PlanviewConnector",
    "ClarityConnector",
    "JiraConnector",
    "AzureDevOpsConnector",
    "SmartsheetConnector",
    "OutlookConnector",
    "GoogleCalendarConnector",
    "ServiceNowConnector",
    "AzureCommunicationConnector",
    "MockIntegrationConnector",
    "default_registry",
]
