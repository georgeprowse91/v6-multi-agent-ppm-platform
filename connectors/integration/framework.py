"""Connector integration framework for external systems."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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
        except Exception as exc:
            logger.warning("Connector health check failed", extra={"error": str(exc)})
            return False


class ConnectorRegistry:
    """Registry for external connectors."""

    def __init__(self) -> None:
        self._registry: Dict[str, Type[BaseIntegrationConnector]] = {}

    def register(self, system: str, connector: Type[BaseIntegrationConnector]) -> None:
        self._registry[system] = connector

    def create(
        self, system: str, config: IntegrationConfig, settings: Optional[ConnectorSettings] = None
    ) -> BaseIntegrationConnector:
        connector_cls = self._registry.get(system)
        if not connector_cls:
            raise ValueError(f"Unknown connector system: {system}")
        return connector_cls(config, settings=settings)

    def list_systems(self) -> list[str]:
        return sorted(self._registry.keys())


class PlanviewConnector(BaseIntegrationConnector):
    system_name = "planview"


class ClarityConnector(BaseIntegrationConnector):
    system_name = "clarity"


class JiraConnector(BaseIntegrationConnector):
    system_name = "jira"


class AzureDevOpsConnector(BaseIntegrationConnector):
    system_name = "azure_devops"


class SmartsheetConnector(BaseIntegrationConnector):
    system_name = "smartsheet"


class OutlookConnector(BaseIntegrationConnector):
    system_name = "outlook"


class GoogleCalendarConnector(BaseIntegrationConnector):
    system_name = "google_calendar"


class ServiceNowConnector(BaseIntegrationConnector):
    system_name = "servicenow"


class AzureCommunicationConnector(BaseIntegrationConnector):
    system_name = "azure_communication"


def default_registry() -> ConnectorRegistry:
    registry = ConnectorRegistry()
    registry.register(PlanviewConnector.system_name, PlanviewConnector)
    registry.register(ClarityConnector.system_name, ClarityConnector)
    registry.register(JiraConnector.system_name, JiraConnector)
    registry.register(AzureDevOpsConnector.system_name, AzureDevOpsConnector)
    registry.register(SmartsheetConnector.system_name, SmartsheetConnector)
    registry.register(OutlookConnector.system_name, OutlookConnector)
    registry.register(GoogleCalendarConnector.system_name, GoogleCalendarConnector)
    registry.register(ServiceNowConnector.system_name, ServiceNowConnector)
    registry.register(AzureCommunicationConnector.system_name, AzureCommunicationConnector)
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
    "default_registry",
]
