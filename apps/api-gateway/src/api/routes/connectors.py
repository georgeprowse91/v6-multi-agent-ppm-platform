"""
Connector API Routes

Provides endpoints for connector management:
- List available connectors
- Get/update connector configurations
- Test connector connections
- Enable/disable connectors with mutual exclusivity
"""

from __future__ import annotations

import hashlib
import hmac
import importlib
import importlib.util
import json
import logging
import os
import re
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import AnyHttpUrl, BaseModel, Field, TypeAdapter, field_validator, model_validator

from api.circuit_breaker import CircuitBreaker
from api.connector_loader import get_connector_class
from feature_flags import is_mcp_feature_enabled

# Add connector SDK to path
REPO_ROOT = Path(__file__).resolve().parents[5]
CONNECTOR_SDK_PATH = REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"
CONNECTORS_ROOT = REPO_ROOT / "integrations" / "connectors"
connector_src_paths = [
    path / "src" for path in CONNECTORS_ROOT.iterdir() if (path / "src").is_dir()
]
for path in [CONNECTOR_SDK_PATH, *connector_src_paths]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from base_connector import (
    ConnectionStatus,
    ConnectorCategory,
    ConnectorConfig,
    ConnectorConfigStore,
    SyncDirection,
    SyncFrequency,
)
from project_connector_store import ProjectConnectorConfig, ProjectConnectorConfigStore
from connector_registry import (
    ConnectorStatus,
    get_all_connectors,
    get_connector_definition,
    get_connectors_by_category,
)
from integrations.connectors.mcp_client.client import MCPClient
from integrations.connectors.mcp_client.errors import (
    MCPAuthenticationError,
    MCPResponseError,
    MCPServerError,
    MCPTransportError,
)
from regulatory_compliance_connector import RegulatoryComplianceConnector
from security.audit_log import build_event, get_audit_log_store

from api.webhook_storage import WebhookEvent, WebhookEventStore

logger = logging.getLogger(__name__)
router = APIRouter()
_URL_ADAPTER = TypeAdapter(AnyHttpUrl)

# Initialize connector config store
# In production, this path should come from environment
_config_store: ConnectorConfigStore | None = None
_project_config_store: ProjectConnectorConfigStore | None = None
_webhook_store: WebhookEventStore | None = None
_circuit_breaker: CircuitBreaker | None = None


def get_config_store() -> ConnectorConfigStore:
    """Get or create the connector config store."""
    global _config_store
    if _config_store is None:
        storage_path = REPO_ROOT / "data" / "connectors" / "config.json"
        _config_store = ConnectorConfigStore(storage_path)
    return _config_store


def get_project_config_store() -> ProjectConnectorConfigStore:
    """Get or create the project connector config store."""
    global _project_config_store
    if _project_config_store is None:
        storage_path = REPO_ROOT / "data" / "connectors" / "project_config.json"
        _project_config_store = ProjectConnectorConfigStore(storage_path)
    return _project_config_store


def get_webhook_store() -> WebhookEventStore:
    global _webhook_store
    if _webhook_store is None:
        storage_path = REPO_ROOT / "data" / "connectors" / "webhooks.json"
        _webhook_store = WebhookEventStore(storage_path)
    return _webhook_store


def get_circuit_breaker() -> CircuitBreaker:
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker.from_env()
    return _circuit_breaker


def get_webhook_handler(connector_id: str) -> Callable[..., Any] | None:
    webhook_path = CONNECTORS_ROOT / connector_id / "src" / "webhooks.py"
    if not webhook_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"{connector_id}_webhooks", webhook_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "handle_webhook", None)


def get_webhook_registrar(connector_id: str) -> Callable[..., Any] | None:
    webhook_path = CONNECTORS_ROOT / connector_id / "src" / "webhooks.py"
    if not webhook_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"{connector_id}_webhooks_register", webhook_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "register_webhook", None)


def get_test_connection_handler(
    connector_id: str,
    *,
    config: ConnectorConfig | None = None,
) -> tuple[str | None, Any]:
    connector_class = get_connector_class(connector_id, config=config)
    if connector_class and callable(getattr(connector_class, "test_connection", None)):
        return ("class", connector_class)

    module_name = f"{connector_id}_connector"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return (None, None)
    handler = getattr(module, "test_connection", None)
    if callable(handler):
        return ("function", handler)
    return (None, None)


def _webhook_secret_env_var(connector_id: str) -> str:
    safe_id = connector_id.upper().replace("-", "_")
    return f"CONNECTOR_{safe_id}_WEBHOOK_SECRET"


def _get_webhook_secret(connector_id: str) -> str | None:
    return os.getenv(_webhook_secret_env_var(connector_id))


def _validate_webhook_signature(connector_id: str, body: bytes, headers: dict[str, str]) -> None:
    secret = _get_webhook_secret(connector_id)
    if not secret:
        raise HTTPException(
            status_code=500,
            detail=f"Webhook secret not configured for connector '{connector_id}'",
        )
    header_secret = headers.get("x-webhook-secret")
    header_signature = headers.get("x-webhook-signature")
    if header_secret:
        if not hmac.compare_digest(header_secret, secret):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        return
    if header_signature:
        computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        candidate = header_signature.removeprefix("sha256=").strip()
        if not hmac.compare_digest(candidate, computed):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        return
    raise HTTPException(status_code=401, detail="Missing webhook signature or secret")


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    filtered = {}
    for key, value in headers.items():
        if key.lower() in {"x-webhook-secret", "x-webhook-signature"}:
            continue
        filtered[key] = value
    return filtered


def _ensure_connector_is_available(definition: Any) -> None:
    if definition.status == ConnectorStatus.COMING_SOON:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Connector '{definition.connector_id}' is not yet available "
                f"(status: {definition.status.value})"
            ),
        )


def _mcp_feature_enabled(system: str, project_id: str | None = None) -> bool:
    return is_mcp_feature_enabled(system=system, project_id=project_id)


# =============================================================================
# Request/Response Models
# =============================================================================


class ConnectorDefinitionResponse(BaseModel):
    """Response model for connector definition."""

    connector_id: str
    name: str
    description: str
    category: str
    system: str
    mcp_server_id: str
    supported_operations: list[str]
    mcp_preferred: bool
    status: str
    icon: str
    supported_sync_directions: list[str]
    auth_type: str
    config_fields: list[dict[str, Any]]
    config_schema: list[dict[str, Any]]
    env_vars: list[str]


def _normalize_tool_map(value: Any, field_name: str = "mcp_tool_map") -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping of tool keys to tool names")
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{field_name} keys must be strings")
        if isinstance(item, str):
            continue
        if isinstance(item, list) and all(isinstance(entry, str) for entry in item):
            continue
        raise ValueError(f"{field_name} values must be strings or list of strings")
    return value


def _split_mcp_scopes(value: str) -> list[str]:
    if not value:
        return []
    return [item for item in re.split(r"[,\s]+", value) if item]


def _normalize_mcp_scopes(value: Any, field_name: str = "mcp_scopes") -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return _split_mcp_scopes(value)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of strings")
    return [item for item in value if item]


class McpConfig(BaseModel):
    server_id: str | None = None
    server_url: AnyHttpUrl | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scope: str | None = None
    scopes: list[str] | None = None
    api_key: str | None = None
    api_key_header: str | None = None
    oauth_token: str | None = None
    tools: list[str] | None = None
    tool_map: dict[str, Any] | None = None

    @field_validator("server_url", mode="before")
    @classmethod
    def _validate_server_url(cls, value: Any) -> Any:
        if value in (None, ""):
            return None
        _URL_ADAPTER.validate_python(value)
        return value

    @field_validator("tools", mode="before")
    @classmethod
    def _validate_tools(cls, value: Any) -> Any:
        if value in (None, ""):
            return None
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("tools must be a list of strings")
        return value

    @field_validator("scopes", mode="before")
    @classmethod
    def _validate_scopes(cls, value: Any) -> list[str] | None:
        if value in (None, ""):
            return None
        return _normalize_mcp_scopes(value, "scopes")

    @field_validator("tool_map", mode="before")
    @classmethod
    def _validate_tool_map(cls, value: Any) -> dict[str, Any] | None:
        if value in (None, ""):
            return None
        return _normalize_tool_map(value, "tool_map")

    @model_validator(mode="after")
    def _normalize_tools(self) -> "McpConfig":
        if self.tool_map is None and self.tools:
            object.__setattr__(self, "tool_map", {tool: tool for tool in self.tools})
        return self


class ConnectorConfigRequest(BaseModel):
    """Request model for creating/updating connector configuration."""

    instance_url: str = ""
    project_key: str = ""
    mcp_server_url: str = ""
    mcp_server_id: str = ""
    mcp_client_id: str = ""
    mcp_client_secret: str = ""
    mcp_scope: str = ""
    mcp_scopes: list[str] = Field(default_factory=list)
    mcp_api_key: str = ""
    mcp_api_key_header: str = ""
    mcp_oauth_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    scope: str = ""
    mcp_tools: list[str] = Field(default_factory=list)
    mcp_tool_map: dict[str, Any] = Field(default_factory=dict)
    mcp_config: McpConfig | None = None
    prefer_mcp: bool = False
    mcp_enabled: bool = True
    mcp_enabled_operations: list[str] = Field(default_factory=list)
    mcp_disabled_operations: list[str] = Field(default_factory=list)
    sync_direction: str = Field(default="inbound", pattern="^(inbound|outbound|bidirectional)$")
    sync_frequency: str = Field(
        default="daily",
        pattern="^(realtime|hourly|every_4_hours|daily|weekly|manual)$",
    )
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    @field_validator("mcp_server_url", mode="before")
    @classmethod
    def _validate_mcp_server_url(cls, value: Any) -> Any:
        if value in (None, ""):
            return ""
        _URL_ADAPTER.validate_python(value)
        return value

    @field_validator("mcp_tool_map", mode="before")
    @classmethod
    def _validate_mcp_tool_map(cls, value: Any) -> dict[str, Any]:
        return _normalize_tool_map(value)

    @field_validator("mcp_tools", mode="before")
    @classmethod
    def _validate_mcp_tools(cls, value: Any) -> list[str]:
        if value in (None, ""):
            return []
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("mcp_tools must be a list of strings")
        return value

    @field_validator("mcp_scopes", mode="before")
    @classmethod
    def _validate_mcp_scopes(cls, value: Any) -> list[str]:
        return _normalize_mcp_scopes(value)

    @model_validator(mode="after")
    def _merge_mcp_config(self) -> "ConnectorConfigRequest":
        if not self.mcp_config:
            if not self.mcp_tool_map and self.mcp_tools:
                self.mcp_tool_map = {tool: tool for tool in self.mcp_tools}
            if not self.mcp_scopes and self.mcp_scope:
                self.mcp_scopes = _split_mcp_scopes(self.mcp_scope)
            if not self.mcp_scope and self.mcp_scopes:
                self.mcp_scope = " ".join(self.mcp_scopes)
            return self
        if not self.mcp_server_id and self.mcp_config.server_id:
            self.mcp_server_id = self.mcp_config.server_id
        if not self.mcp_server_url and self.mcp_config.server_url:
            self.mcp_server_url = str(self.mcp_config.server_url)
        if not self.mcp_client_id and self.mcp_config.client_id:
            self.mcp_client_id = self.mcp_config.client_id
        if not self.mcp_client_secret and self.mcp_config.client_secret:
            self.mcp_client_secret = self.mcp_config.client_secret
        if not self.mcp_scope and self.mcp_config.scope:
            self.mcp_scope = self.mcp_config.scope
        if not self.mcp_scopes and self.mcp_config.scopes:
            self.mcp_scopes = self.mcp_config.scopes
        if not self.mcp_scopes and self.mcp_scope:
            self.mcp_scopes = _split_mcp_scopes(self.mcp_scope)
        if not self.mcp_scope and self.mcp_scopes:
            self.mcp_scope = " ".join(self.mcp_scopes)
        if not self.mcp_api_key and self.mcp_config.api_key:
            self.mcp_api_key = self.mcp_config.api_key
        if not self.mcp_api_key_header and self.mcp_config.api_key_header:
            self.mcp_api_key_header = self.mcp_config.api_key_header
        if not self.mcp_oauth_token and self.mcp_config.oauth_token:
            self.mcp_oauth_token = self.mcp_config.oauth_token
        if not self.mcp_tool_map and self.mcp_config.tool_map:
            self.mcp_tool_map = self.mcp_config.tool_map
        if not self.mcp_tool_map and self.mcp_tools:
            self.mcp_tool_map = {tool: tool for tool in self.mcp_tools}
        return self


class ConnectorConfigResponse(BaseModel):
    """Response model for connector configuration."""

    connector_id: str
    name: str
    category: str
    enabled: bool
    sync_direction: str
    sync_frequency: str
    instance_url: str
    project_key: str
    custom_fields: dict[str, Any]
    mcp_server_url: str
    mcp_server_id: str
    mcp_client_id: str
    mcp_client_secret: str
    mcp_scope: str
    mcp_scopes: list[str] = Field(default_factory=list)
    mcp_api_key: str
    mcp_api_key_header: str
    mcp_oauth_token: str
    client_id: str
    client_secret: str
    scope: str
    mcp_tool_map: dict[str, Any]
    mcp_config: McpConfig | None = None
    prefer_mcp: bool
    mcp_enabled: bool
    mcp_feature_enabled: bool
    mcp_enabled_operations: list[str]
    mcp_disabled_operations: list[str]
    health_status: str
    created_at: str
    updated_at: str
    last_sync_at: str | None

    @field_validator("mcp_tool_map", mode="before")
    @classmethod
    def _validate_mcp_tool_map(cls, value: Any) -> dict[str, Any]:
        return _normalize_tool_map(value)

    @model_validator(mode="after")
    def _populate_mcp_config(self) -> "ConnectorConfigResponse":
        if self.mcp_config is None:
            tool_map = self.mcp_tool_map or None
            if any(
                [
                    self.mcp_server_id,
                    self.mcp_server_url,
                    self.mcp_client_id,
                    self.mcp_client_secret,
                    self.mcp_scope,
                    self.mcp_api_key,
                    self.mcp_api_key_header,
                    self.mcp_oauth_token,
                    self.mcp_scopes,
                    tool_map,
                ]
            ):
                self.mcp_config = McpConfig(
                    server_id=self.mcp_server_id or None,
                    server_url=self.mcp_server_url or None,
                    client_id=self.mcp_client_id or None,
                    client_secret=self.mcp_client_secret or None,
                    scope=self.mcp_scope or None,
                    scopes=self.mcp_scopes or _split_mcp_scopes(self.mcp_scope),
                    api_key=self.mcp_api_key or None,
                    api_key_header=self.mcp_api_key_header or None,
                    oauth_token=self.mcp_oauth_token or None,
                    tool_map=tool_map,
                )
        if not self.mcp_scopes and self.mcp_scope:
            self.mcp_scopes = _split_mcp_scopes(self.mcp_scope)
        return self


class ProjectConnectorConfigResponse(BaseModel):
    connector_id: str
    project_id: str
    name: str
    category: str
    enabled: bool
    sync_direction: str
    sync_frequency: str
    instance_url: str
    project_key: str
    custom_fields: dict[str, Any]
    mcp_server_url: str
    mcp_server_id: str
    mcp_client_id: str
    mcp_client_secret: str
    mcp_scope: str
    mcp_scopes: list[str] = Field(default_factory=list)
    mcp_api_key: str
    mcp_api_key_header: str
    mcp_oauth_token: str
    client_id: str
    client_secret: str
    scope: str
    mcp_tools: list[str]
    mcp_tool_map: dict[str, Any]
    mcp_config: McpConfig | None = None
    prefer_mcp: bool
    mcp_enabled: bool
    mcp_feature_enabled: bool
    mcp_enabled_operations: list[str]
    mcp_disabled_operations: list[str]
    health_status: str
    created_at: str
    updated_at: str
    last_sync_at: str | None

    @field_validator("mcp_tool_map", mode="before")
    @classmethod
    def _validate_mcp_tool_map(cls, value: Any) -> dict[str, Any]:
        return _normalize_tool_map(value)

    @model_validator(mode="after")
    def _populate_mcp_config(self) -> "ProjectConnectorConfigResponse":
        if self.mcp_config is None:
            tool_map = self.mcp_tool_map or {tool: tool for tool in self.mcp_tools} or None
            if any(
                [
                    self.mcp_server_id,
                    self.mcp_server_url,
                    self.mcp_client_id,
                    self.mcp_client_secret,
                    self.mcp_scope,
                    self.mcp_api_key,
                    self.mcp_api_key_header,
                    self.mcp_oauth_token,
                    self.mcp_scopes,
                    tool_map,
                ]
            ):
                self.mcp_config = McpConfig(
                    server_id=self.mcp_server_id or None,
                    server_url=self.mcp_server_url or None,
                    client_id=self.mcp_client_id or None,
                    client_secret=self.mcp_client_secret or None,
                    scope=self.mcp_scope or None,
                    scopes=self.mcp_scopes or _split_mcp_scopes(self.mcp_scope),
                    api_key=self.mcp_api_key or None,
                    api_key_header=self.mcp_api_key_header or None,
                    oauth_token=self.mcp_oauth_token or None,
                    tool_map=tool_map,
                )
        if not self.mcp_scopes and self.mcp_scope:
            self.mcp_scopes = _split_mcp_scopes(self.mcp_scope)
        return self


class ConnectorListItemResponse(BaseModel):
    """Response model for connector list items (combines definition and config)."""

    # Definition fields
    connector_id: str
    name: str
    description: str
    category: str
    system: str
    mcp_server_id: str
    supported_operations: list[str]
    mcp_preferred: bool
    status: str  # available, coming_soon, beta
    icon: str
    supported_sync_directions: list[str]
    auth_type: str
    config_fields: list[dict[str, Any]]
    config_schema: list[dict[str, Any]]
    env_vars: list[str]

    # Config fields (if configured)
    enabled: bool = False
    configured: bool = False
    instance_url: str = ""
    project_key: str = ""
    sync_direction: str = "inbound"
    sync_frequency: str = "daily"
    health_status: str = "unknown"
    last_sync_at: str | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    mcp_server_url: str = ""
    mcp_server_id: str = ""
    mcp_client_id: str = ""
    mcp_client_secret: str = ""
    mcp_scope: str = ""
    mcp_scopes: list[str] = Field(default_factory=list)
    mcp_api_key: str = ""
    mcp_api_key_header: str = ""
    mcp_oauth_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    scope: str = ""
    mcp_tools: list[str] = Field(default_factory=list)
    mcp_tool_map: dict[str, Any] = Field(default_factory=dict)
    prefer_mcp: bool = False
    mcp_enabled: bool = True
    mcp_feature_enabled: bool = True
    mcp_enabled_operations: list[str] = Field(default_factory=list)
    mcp_disabled_operations: list[str] = Field(default_factory=list)


class ProjectConnectorListItemResponse(ConnectorListItemResponse):
    project_id: str


class TestConnectionRequest(BaseModel):
    """Request model for testing connection."""

    instance_url: str = ""
    project_key: str = ""


class TestConnectionResponse(BaseModel):
    """Response model for connection test result."""

    status: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    tested_at: str


class CategoryInfo(BaseModel):
    """Information about a connector category."""

    value: str
    label: str
    icon: str
    description: str
    connector_count: int
    enabled_connector: str | None = None


class RegulatoryComplianceConfigRequest(BaseModel):
    endpoint_url: str = ""
    api_key: str = ""
    supported_regulations: list[str] = Field(default_factory=list)


class McpToolSchemaResponse(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)


class McpServerToolsResponse(BaseModel):
    system: str
    server_id: str
    server_url: str
    tools: list[McpToolSchemaResponse]


class ProjectMcpConfigRequest(BaseModel):
    mcp_server_url: AnyHttpUrl
    mcp_server_id: str | None = None
    mcp_tools: list[str] | None = None
    mcp_tool_map: dict[str, Any] = Field(default_factory=dict)

    @field_validator("mcp_server_url", mode="before")
    @classmethod
    def _validate_mcp_server_url(cls, value: Any) -> Any:
        if value in (None, ""):
            raise ValueError("mcp_server_url is required")
        _URL_ADAPTER.validate_python(value)
        return value

    @field_validator("mcp_tool_map", mode="before")
    @classmethod
    def _validate_mcp_tool_map(cls, value: Any) -> dict[str, Any]:
        return _normalize_tool_map(value)

    @field_validator("mcp_tools", mode="before")
    @classmethod
    def _validate_mcp_tools(cls, value: Any) -> list[str] | None:
        if value in (None, ""):
            return None
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("mcp_tools must be a list of strings")
        return value

    @model_validator(mode="after")
    def _normalize_tools(self) -> "ProjectMcpConfigRequest":
        if not self.mcp_tool_map and self.mcp_tools:
            self.mcp_tool_map = {tool: tool for tool in self.mcp_tools}
        return self


class ProjectMcpConfigResponse(BaseModel):
    connector_id: str
    project_id: str
    enabled: bool
    mcp_server_url: str
    mcp_server_id: str
    mcp_tool_map: dict[str, Any]
    mcp_tools: list[str]
    updated_at: str


# =============================================================================
# Endpoints
# =============================================================================


def _get_mcp_definition_by_system(system: str) -> Any:
    definitions = [definition for definition in get_all_connectors() if definition.system == system]
    if not definitions:
        raise HTTPException(status_code=404, detail=f"MCP server not found: {system}")
    for definition in definitions:
        if definition.auth_type == "mcp":
            return definition
    raise HTTPException(status_code=404, detail=f"MCP connector not found for system: {system}")


def _build_project_mcp_response(
    project_id: str, config: ProjectConnectorConfig
) -> ProjectMcpConfigResponse:
    return ProjectMcpConfigResponse(
        connector_id=config.connector_id,
        project_id=project_id,
        enabled=config.enabled,
        mcp_server_url=config.mcp_server_url,
        mcp_server_id=config.mcp_server_id,
        mcp_tool_map=config.mcp_tool_map,
        mcp_tools=config.mcp_tools or list(config.mcp_tool_map.keys()),
        updated_at=config.updated_at.isoformat(),
    )


@router.get("/connectors/categories", response_model=list[CategoryInfo])
async def list_categories(
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[CategoryInfo]:
    """
    List all connector categories with their metadata.
    """
    category_info = {
        ConnectorCategory.PPM: {
            "label": "PPM Tools",
            "icon": "chart-bar",
            "description": "Portfolio and Project Management platforms",
        },
        ConnectorCategory.PM: {
            "label": "PM Tools",
            "icon": "clipboard-list",
            "description": "Project management and work tracking tools",
        },
        ConnectorCategory.DOC_MGMT: {
            "label": "Document Management",
            "icon": "folder",
            "description": "Document storage and collaboration platforms",
        },
        ConnectorCategory.ERP: {
            "label": "ERP Systems",
            "icon": "building-office",
            "description": "Enterprise resource planning systems",
        },
        ConnectorCategory.HRIS: {
            "label": "HRIS",
            "icon": "users",
            "description": "Human resource information systems",
        },
        ConnectorCategory.COLLABORATION: {
            "label": "Collaboration",
            "icon": "chat-bubble-left-right",
            "description": "Team communication and collaboration tools",
        },
        ConnectorCategory.GRC: {
            "label": "GRC",
            "icon": "shield-check",
            "description": "Governance, Risk, and Compliance platforms",
        },
        ConnectorCategory.COMPLIANCE: {
            "label": "Compliance",
            "icon": "shield-check",
            "description": "Specialised regulatory compliance integrations",
        },
    }

    store = get_config_store()
    categories = []

    for category in ConnectorCategory:
        info = category_info.get(category, {"label": category.value, "icon": "", "description": ""})
        connectors = get_connectors_by_category(category)
        enabled_config = store.get_enabled_by_category(category)

        categories.append(
            CategoryInfo(
                value=category.value,
                label=info["label"],
                icon=info["icon"],
                description=info["description"],
                connector_count=len(connectors),
                enabled_connector=enabled_config.connector_id if enabled_config else None,
            )
        )

    sliced = categories[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(categories))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@router.get("/mcp/servers/{system}/tools", response_model=McpServerToolsResponse)
async def list_mcp_server_tools(system: str) -> McpServerToolsResponse:
    """
    List available MCP tools for a specific server/system.
    """
    definition = _get_mcp_definition_by_system(system)
    config_store = get_config_store()
    config = config_store.get(definition.connector_id)
    if not config or not config.mcp_server_url:
        raise HTTPException(
            status_code=404,
            detail=f"MCP configuration missing for system: {system}",
        )

    server_id = config.mcp_server_id or definition.mcp_server_id or system
    client = MCPClient(
        mcp_server_id=server_id,
        mcp_server_url=config.mcp_server_url,
        config=config,
    )
    try:
        tools = await client.list_tools()
    except MCPAuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except (MCPTransportError, MCPResponseError, MCPServerError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return McpServerToolsResponse(
        system=system,
        server_id=server_id,
        server_url=config.mcp_server_url,
        tools=[
            McpToolSchemaResponse(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
            )
            for tool in tools
        ],
    )


@router.get("/connectors", response_model=list[ConnectorListItemResponse])
async def list_connectors(
    response: Response,
    category: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[ConnectorListItemResponse]:
    """
    List all available connectors with their configuration status.

    Optionally filter by category.
    """
    store = get_config_store()

    # Get connector definitions
    if category:
        try:
            cat = ConnectorCategory(category)
            definitions = get_connectors_by_category(cat)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    else:
        definitions = get_all_connectors()

    # Merge with configurations
    result = []
    for definition in definitions:
        config = store.get(definition.connector_id)

        item = ConnectorListItemResponse(
            connector_id=definition.connector_id,
            name=definition.name,
            description=definition.description,
            category=definition.category.value,
            system=definition.system,
            mcp_server_id=definition.mcp_server_id,
            supported_operations=definition.supported_operations,
            mcp_preferred=definition.mcp_preferred,
            status=definition.status.value,
            icon=definition.icon,
            supported_sync_directions=[d.value for d in definition.supported_sync_directions],
            auth_type=definition.auth_type,
            config_fields=definition.config_fields,
            config_schema=definition.config_schema or definition.config_fields,
            env_vars=definition.env_vars,
            enabled=config.enabled if config else False,
            configured=config is not None,
            instance_url=config.instance_url if config else "",
            project_key=config.project_key if config else "",
            sync_direction=config.sync_direction.value if config else "inbound",
            sync_frequency=config.sync_frequency.value if config else "daily",
            health_status=config.health_status if config else "unknown",
            last_sync_at=(
                config.last_sync_at.isoformat() if config and config.last_sync_at else None
            ),
            custom_fields=config.custom_fields if config else {},
            mcp_server_url=config.mcp_server_url if config else "",
            mcp_server_id=config.mcp_server_id if config else "",
            mcp_client_id=config.mcp_client_id if config else "",
            mcp_client_secret=config.mcp_client_secret if config else "",
            mcp_scope=config.mcp_scope if config else "",
            mcp_scopes=(
                config.mcp_scopes
                if config and config.mcp_scopes
                else (_split_mcp_scopes(config.mcp_scope) if config else [])
            ),
            mcp_api_key=config.mcp_api_key if config else "",
            mcp_api_key_header=config.mcp_api_key_header if config else "",
            mcp_oauth_token=config.mcp_oauth_token if config else "",
            client_id=config.client_id if config else "",
            client_secret=config.client_secret if config else "",
            scope=config.scope if config else "",
            mcp_tools=list(config.mcp_tool_map.keys()) if config and config.mcp_tool_map else [],
            mcp_tool_map=config.mcp_tool_map if config else {},
            prefer_mcp=config.prefer_mcp if config else False,
            mcp_enabled=config.mcp_enabled if config else True,
            mcp_feature_enabled=_mcp_feature_enabled(definition.system),
            mcp_enabled_operations=config.mcp_enabled_operations if config else [],
            mcp_disabled_operations=config.mcp_disabled_operations if config else [],
        )
        result.append(item)

    sliced = result[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(result))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@router.get("/projects/{project_id}/connectors", response_model=list[ProjectConnectorListItemResponse])
async def list_project_connectors(
    project_id: str,
    response: Response,
    category: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[ProjectConnectorListItemResponse]:
    """
    List connectors with project-scoped configuration.
    """
    store = get_project_config_store()
    base_store = get_config_store()

    if category:
        try:
            cat = ConnectorCategory(category)
            definitions = get_connectors_by_category(cat)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    else:
        definitions = get_all_connectors()

    result: list[ProjectConnectorListItemResponse] = []
    for definition in definitions:
        project_config = store.get(project_id, definition.connector_id)
        global_config = base_store.get(definition.connector_id)
        result.append(
            ProjectConnectorListItemResponse(
                project_id=project_id,
                connector_id=definition.connector_id,
                name=definition.name,
                description=definition.description,
                category=definition.category.value,
                system=definition.system,
                mcp_server_id=definition.mcp_server_id,
                supported_operations=definition.supported_operations,
                mcp_preferred=definition.mcp_preferred,
                status=definition.status.value,
                icon=definition.icon,
                supported_sync_directions=[d.value for d in definition.supported_sync_directions],
                auth_type=definition.auth_type,
                config_fields=definition.config_fields,
                config_schema=definition.config_schema or definition.config_fields,
                env_vars=definition.env_vars,
                enabled=project_config.enabled if project_config else False,
                configured=project_config is not None,
                instance_url=project_config.instance_url if project_config else "",
                project_key=project_config.project_key if project_config else "",
                sync_direction=(
                    project_config.sync_direction.value
                    if project_config
                    else (global_config.sync_direction.value if global_config else "inbound")
                ),
                sync_frequency=(
                    project_config.sync_frequency.value
                    if project_config
                    else (global_config.sync_frequency.value if global_config else "daily")
                ),
                health_status=(
                    project_config.health_status
                    if project_config
                    else (global_config.health_status if global_config else "unknown")
                ),
                last_sync_at=(
                    project_config.last_sync_at.isoformat()
                    if project_config and project_config.last_sync_at
                    else None
                ),
                custom_fields=project_config.custom_fields if project_config else {},
                mcp_server_url=project_config.mcp_server_url if project_config else "",
                mcp_server_id=project_config.mcp_server_id if project_config else "",
                mcp_client_id=project_config.mcp_client_id if project_config else "",
                mcp_client_secret=project_config.mcp_client_secret if project_config else "",
                mcp_scope=project_config.mcp_scope if project_config else "",
                mcp_scopes=(
                    project_config.mcp_scopes
                    if project_config and project_config.mcp_scopes
                    else (
                        _split_mcp_scopes(project_config.mcp_scope)
                        if project_config
                        else []
                    )
                ),
                mcp_api_key=project_config.mcp_api_key if project_config else "",
                mcp_api_key_header=project_config.mcp_api_key_header if project_config else "",
                mcp_oauth_token=project_config.mcp_oauth_token if project_config else "",
                client_id=project_config.client_id if project_config else "",
                client_secret=project_config.client_secret if project_config else "",
                scope=project_config.scope if project_config else "",
                mcp_tools=(
                    project_config.mcp_tools
                    if project_config and project_config.mcp_tools
                    else (
                        list(project_config.mcp_tool_map.keys())
                        if project_config and project_config.mcp_tool_map
                        else []
                    )
                ),
                mcp_tool_map=project_config.mcp_tool_map if project_config else {},
                prefer_mcp=project_config.prefer_mcp if project_config else False,
                mcp_enabled=project_config.mcp_enabled if project_config else True,
                mcp_feature_enabled=_mcp_feature_enabled(definition.system, project_id),
                mcp_enabled_operations=(
                    project_config.mcp_enabled_operations if project_config else []
                ),
                mcp_disabled_operations=(
                    project_config.mcp_disabled_operations if project_config else []
                ),
            )
        )

    sliced = result[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(result))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@router.get("/connectors/{connector_id}", response_model=ConnectorListItemResponse)
async def get_connector(connector_id: str) -> ConnectorListItemResponse:
    """
    Get a specific connector with its configuration.
    """
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    store = get_config_store()
    config = store.get(connector_id)

    return ConnectorListItemResponse(
        connector_id=definition.connector_id,
        name=definition.name,
        description=definition.description,
        category=definition.category.value,
        system=definition.system,
        mcp_server_id=definition.mcp_server_id,
        supported_operations=definition.supported_operations,
        mcp_preferred=definition.mcp_preferred,
        status=definition.status.value,
        icon=definition.icon,
        supported_sync_directions=[d.value for d in definition.supported_sync_directions],
        auth_type=definition.auth_type,
        config_fields=definition.config_fields,
        config_schema=definition.config_schema or definition.config_fields,
        env_vars=definition.env_vars,
        enabled=config.enabled if config else False,
        configured=config is not None,
        instance_url=config.instance_url if config else "",
        project_key=config.project_key if config else "",
        sync_direction=config.sync_direction.value if config else "inbound",
        sync_frequency=config.sync_frequency.value if config else "daily",
        health_status=config.health_status if config else "unknown",
        last_sync_at=config.last_sync_at.isoformat() if config and config.last_sync_at else None,
        custom_fields=config.custom_fields if config else {},
        mcp_server_url=config.mcp_server_url if config else "",
        mcp_server_id=config.mcp_server_id if config else "",
        mcp_client_id=config.mcp_client_id if config else "",
        mcp_client_secret=config.mcp_client_secret if config else "",
        mcp_scope=config.mcp_scope if config else "",
        mcp_scopes=(
            config.mcp_scopes
            if config and config.mcp_scopes
            else (_split_mcp_scopes(config.mcp_scope) if config else [])
        ),
        mcp_api_key=config.mcp_api_key if config else "",
        mcp_api_key_header=config.mcp_api_key_header if config else "",
        mcp_oauth_token=config.mcp_oauth_token if config else "",
        client_id=config.client_id if config else "",
        client_secret=config.client_secret if config else "",
        scope=config.scope if config else "",
        mcp_tools=list(config.mcp_tool_map.keys()) if config and config.mcp_tool_map else [],
        mcp_tool_map=config.mcp_tool_map if config else {},
        prefer_mcp=config.prefer_mcp if config else False,
        mcp_enabled=config.mcp_enabled if config else True,
        mcp_feature_enabled=_mcp_feature_enabled(definition.system),
        mcp_enabled_operations=config.mcp_enabled_operations if config else [],
        mcp_disabled_operations=config.mcp_disabled_operations if config else [],
    )


@router.put("/connectors/{connector_id}/config", response_model=ConnectorConfigResponse)
async def update_connector_config(
    connector_id: str, request: ConnectorConfigRequest, http_request: Request
) -> ConnectorConfigResponse:
    """
    Update connector configuration.

    Note: This only stores non-secret configuration.
    Secrets (API tokens, passwords) must be provided via environment variables.
    """
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    store = get_config_store()
    existing = store.get(connector_id)

    now = datetime.now(timezone.utc)

    config = ConnectorConfig(
        connector_id=connector_id,
        name=definition.name,
        category=definition.category,
        enabled=existing.enabled if existing else False,
        sync_direction=SyncDirection(request.sync_direction),
        sync_frequency=SyncFrequency(request.sync_frequency),
        instance_url=request.instance_url,
        project_key=request.project_key,
        custom_fields=request.custom_fields,
        mcp_server_url=request.mcp_server_url,
        mcp_server_id=request.mcp_server_id,
        mcp_client_id=request.mcp_client_id,
        mcp_client_secret=request.mcp_client_secret,
        mcp_scope=request.mcp_scope,
        mcp_scopes=request.mcp_scopes,
        mcp_api_key=request.mcp_api_key,
        mcp_api_key_header=request.mcp_api_key_header,
        mcp_oauth_token=request.mcp_oauth_token,
        client_id=request.client_id,
        client_secret=request.client_secret,
        scope=request.scope,
        mcp_tool_map=request.mcp_tool_map,
        prefer_mcp=request.prefer_mcp,
        mcp_enabled=request.mcp_enabled,
        mcp_enabled_operations=request.mcp_enabled_operations,
        mcp_disabled_operations=request.mcp_disabled_operations,
        created_at=existing.created_at if existing else now,
        updated_at=now,
        last_sync_at=existing.last_sync_at if existing else None,
        health_status=existing.health_status if existing else "unknown",
    )

    store.save(config)

    auth = http_request.state.auth
    get_audit_log_store().record_event(
        build_event(
            tenant_id=auth.tenant_id,
            actor_id=auth.subject,
            actor_type="user",
            roles=auth.roles,
            action="connector.config.updated",
            resource_type="connector",
            resource_id=connector_id,
            outcome="success",
            metadata={"enabled": config.enabled},
        )
    )

    return ConnectorConfigResponse(
        connector_id=config.connector_id,
        name=config.name,
        category=config.category.value,
        enabled=config.enabled,
        sync_direction=config.sync_direction.value,
        sync_frequency=config.sync_frequency.value,
        instance_url=config.instance_url,
        project_key=config.project_key,
        custom_fields=config.custom_fields,
        mcp_server_url=config.mcp_server_url,
        mcp_server_id=config.mcp_server_id,
        mcp_client_id=config.mcp_client_id,
        mcp_client_secret=config.mcp_client_secret,
        mcp_scope=config.mcp_scope,
        mcp_scopes=config.mcp_scopes,
        mcp_api_key=config.mcp_api_key,
        mcp_api_key_header=config.mcp_api_key_header,
        mcp_oauth_token=config.mcp_oauth_token,
        client_id=config.client_id,
        client_secret=config.client_secret,
        scope=config.scope,
        mcp_tool_map=config.mcp_tool_map,
        prefer_mcp=config.prefer_mcp,
        mcp_enabled=config.mcp_enabled,
        mcp_feature_enabled=_mcp_feature_enabled(definition.system),
        mcp_enabled_operations=config.mcp_enabled_operations,
        mcp_disabled_operations=config.mcp_disabled_operations,
        health_status=config.health_status,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
    )


@router.put(
    "/projects/{project_id}/connectors/{connector_id}/config",
    response_model=ProjectConnectorConfigResponse,
)
async def update_project_connector_config(
    project_id: str,
    connector_id: str,
    request: ConnectorConfigRequest,
) -> ProjectConnectorConfigResponse:
    """
    Update project-scoped connector configuration.
    """
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    store = get_project_config_store()
    existing = store.get(project_id, connector_id)
    now = datetime.now(timezone.utc)

    config = ProjectConnectorConfig(
        ppm_project_id=project_id,
        connector_id=connector_id,
        name=definition.name,
        category=definition.category,
        enabled=existing.enabled if existing else False,
        sync_direction=SyncDirection(request.sync_direction),
        sync_frequency=SyncFrequency(request.sync_frequency),
        instance_url=request.instance_url,
        project_key=request.project_key,
        custom_fields=request.custom_fields or {},
        mcp_server_url=request.mcp_server_url,
        mcp_server_id=request.mcp_server_id,
        mcp_client_id=request.mcp_client_id,
        mcp_client_secret=request.mcp_client_secret,
        mcp_scope=request.mcp_scope,
        mcp_scopes=request.mcp_scopes,
        mcp_api_key=request.mcp_api_key,
        mcp_api_key_header=request.mcp_api_key_header,
        mcp_oauth_token=request.mcp_oauth_token,
        client_id=request.client_id,
        client_secret=request.client_secret,
        scope=request.scope,
        mcp_tools=request.mcp_tools or list(request.mcp_tool_map.keys()),
        mcp_tool_map=request.mcp_tool_map,
        prefer_mcp=request.prefer_mcp,
        mcp_enabled=request.mcp_enabled,
        mcp_enabled_operations=request.mcp_enabled_operations,
        mcp_disabled_operations=request.mcp_disabled_operations,
        created_at=existing.created_at if existing else now,
        updated_at=now,
        last_sync_at=existing.last_sync_at if existing else None,
        health_status=existing.health_status if existing else "unknown",
    )

    store.save(config)

    return ProjectConnectorConfigResponse(
        connector_id=config.connector_id,
        project_id=config.ppm_project_id,
        name=config.name,
        category=config.category.value,
        enabled=config.enabled,
        sync_direction=config.sync_direction.value,
        sync_frequency=config.sync_frequency.value,
        instance_url=config.instance_url,
        project_key=config.project_key,
        custom_fields=config.custom_fields,
        mcp_server_url=config.mcp_server_url,
        mcp_server_id=config.mcp_server_id,
        mcp_client_id=config.mcp_client_id,
        mcp_client_secret=config.mcp_client_secret,
        mcp_scope=config.mcp_scope,
        mcp_scopes=config.mcp_scopes,
        mcp_api_key=config.mcp_api_key,
        mcp_api_key_header=config.mcp_api_key_header,
        mcp_oauth_token=config.mcp_oauth_token,
        client_id=config.client_id,
        client_secret=config.client_secret,
        scope=config.scope,
        mcp_tool_map=config.mcp_tool_map,
        prefer_mcp=config.prefer_mcp,
        mcp_enabled=config.mcp_enabled,
        mcp_feature_enabled=_mcp_feature_enabled(definition.system, project_id),
        mcp_enabled_operations=config.mcp_enabled_operations,
        mcp_disabled_operations=config.mcp_disabled_operations,
        health_status=config.health_status,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
    )


@router.put("/connectors/regulatory_compliance/config", response_model=ConnectorConfigResponse)
async def update_regulatory_compliance_config(
    request: RegulatoryComplianceConfigRequest, http_request: Request
) -> ConnectorConfigResponse:
    connector_id = "regulatory_compliance"
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    store = get_config_store()
    existing = store.get(connector_id)
    now = datetime.now(timezone.utc)
    custom_fields = dict(existing.custom_fields) if existing else {}
    if request.endpoint_url:
        custom_fields["endpoint_url"] = request.endpoint_url
    if request.supported_regulations:
        custom_fields["supported_regulations"] = request.supported_regulations
    if request.api_key:
        custom_fields["api_key"] = request.api_key

    config = ConnectorConfig(
        connector_id=connector_id,
        name=definition.name,
        category=definition.category,
        enabled=existing.enabled if existing else False,
        sync_direction=SyncDirection.INBOUND,
        sync_frequency=SyncFrequency.DAILY,
        instance_url=request.endpoint_url or (existing.instance_url if existing else ""),
        project_key=existing.project_key if existing else "",
        custom_fields=custom_fields,
        mcp_server_url=existing.mcp_server_url if existing else "",
        mcp_server_id=existing.mcp_server_id if existing else "",
        mcp_client_id=existing.mcp_client_id if existing else "",
        mcp_client_secret=existing.mcp_client_secret if existing else "",
        mcp_scope=existing.mcp_scope if existing else "",
        mcp_scopes=(
            existing.mcp_scopes
            if existing and existing.mcp_scopes
            else (_split_mcp_scopes(existing.mcp_scope) if existing else [])
        ),
        mcp_api_key=existing.mcp_api_key if existing else "",
        mcp_api_key_header=existing.mcp_api_key_header if existing else "",
        mcp_oauth_token=existing.mcp_oauth_token if existing else "",
        client_id=existing.client_id if existing else "",
        client_secret=existing.client_secret if existing else "",
        scope=existing.scope if existing else "",
        mcp_tool_map=existing.mcp_tool_map if existing else {},
        prefer_mcp=existing.prefer_mcp if existing else False,
        mcp_enabled=existing.mcp_enabled if existing else True,
        mcp_enabled_operations=existing.mcp_enabled_operations if existing else [],
        mcp_disabled_operations=existing.mcp_disabled_operations if existing else [],
        created_at=existing.created_at if existing else now,
        updated_at=now,
        last_sync_at=existing.last_sync_at if existing else None,
        health_status=existing.health_status if existing else "unknown",
    )

    store.save(config)

    auth = http_request.state.auth
    get_audit_log_store().record_event(
        build_event(
            tenant_id=auth.tenant_id,
            actor_id=auth.subject,
            actor_type="user",
            roles=auth.roles,
            action="connector.config.updated",
            resource_type="connector",
            resource_id=connector_id,
            outcome="success",
            metadata={"enabled": config.enabled},
        )
    )

    return ConnectorConfigResponse(
        connector_id=config.connector_id,
        name=config.name,
        category=config.category.value,
        enabled=config.enabled,
        sync_direction=config.sync_direction.value,
        sync_frequency=config.sync_frequency.value,
        instance_url=config.instance_url,
        project_key=config.project_key,
        custom_fields=config.custom_fields,
        mcp_server_url=config.mcp_server_url,
        mcp_server_id=config.mcp_server_id,
        mcp_client_id=config.mcp_client_id,
        mcp_client_secret=config.mcp_client_secret,
        mcp_scope=config.mcp_scope,
        mcp_scopes=config.mcp_scopes,
        mcp_api_key=config.mcp_api_key,
        mcp_api_key_header=config.mcp_api_key_header,
        mcp_oauth_token=config.mcp_oauth_token,
        client_id=config.client_id,
        client_secret=config.client_secret,
        scope=config.scope,
        mcp_tool_map=config.mcp_tool_map,
        prefer_mcp=config.prefer_mcp,
        mcp_enabled=config.mcp_enabled,
        mcp_feature_enabled=_mcp_feature_enabled(definition.system),
        mcp_enabled_operations=config.mcp_enabled_operations,
        mcp_disabled_operations=config.mcp_disabled_operations,
        health_status=config.health_status,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
    )


@router.post("/connectors/{connector_id}/enable", response_model=ConnectorConfigResponse)
async def enable_connector(connector_id: str, http_request: Request) -> ConnectorConfigResponse:
    """
    Enable a connector.

    This will disable any other connector in the same category (mutual exclusivity).
    """
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    _ensure_connector_is_available(definition)

    store = get_config_store()

    # Create config if it doesn't exist
    config = store.get(connector_id)

    auth = http_request.state.auth
    get_audit_log_store().record_event(
        build_event(
            tenant_id=auth.tenant_id,
            actor_id=auth.subject,
            actor_type="user",
            roles=auth.roles,
            action="connector.enabled",
            resource_type="connector",
            resource_id=connector_id,
            outcome="success",
        )
    )
    if not config:
        config = ConnectorConfig(
            connector_id=connector_id,
            name=definition.name,
            category=definition.category,
        )
        store.save(config)

    # Enable with mutual exclusivity
    store.enable_connector(connector_id)
    config = store.get(connector_id)

    registrar = get_webhook_registrar(connector_id)
    if registrar and config:
        webhook_url = f"{http_request.base_url}api/v1/connectors/{connector_id}/webhook"
        secret = _get_webhook_secret(connector_id)
        registration_payload: dict[str, Any] = {
            "url": webhook_url,
            "status": "skipped",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if not secret:
            registration_payload["status"] = "skipped"
            registration_payload["reason"] = "missing_secret"
            logger.warning(
                "Webhook registration skipped; secret not configured for %s", connector_id
            )
        else:
            try:
                registration_response = registrar(webhook_url, secret, config)
                registration_payload["status"] = "registered"
                if isinstance(registration_response, dict):
                    registration_payload.update(
                        {
                            key: value
                            for key, value in registration_response.items()
                            if key != "secret"
                        }
                    )
            except (ConnectionError, RuntimeError, TimeoutError, TypeError, ValueError) as exc:
                registration_payload["status"] = "failed"
                registration_payload["reason"] = str(exc)
                logger.exception("Webhook registration failed for %s", connector_id)

        config.custom_fields = config.custom_fields or {}
        config.custom_fields["webhook"] = registration_payload
        store.save(config)

    return ConnectorConfigResponse(
        connector_id=config.connector_id,
        name=config.name,
        category=config.category.value,
        enabled=config.enabled,
        sync_direction=config.sync_direction.value,
        sync_frequency=config.sync_frequency.value,
        instance_url=config.instance_url,
        project_key=config.project_key,
        custom_fields=config.custom_fields,
        mcp_server_url=config.mcp_server_url,
        mcp_server_id=config.mcp_server_id,
        mcp_client_id=config.mcp_client_id,
        mcp_client_secret=config.mcp_client_secret,
        mcp_scope=config.mcp_scope,
        mcp_scopes=config.mcp_scopes,
        mcp_api_key=config.mcp_api_key,
        mcp_api_key_header=config.mcp_api_key_header,
        mcp_oauth_token=config.mcp_oauth_token,
        client_id=config.client_id,
        client_secret=config.client_secret,
        scope=config.scope,
        mcp_tools=config.mcp_tools or list(config.mcp_tool_map.keys()),
        mcp_tool_map=config.mcp_tool_map,
        prefer_mcp=config.prefer_mcp,
        mcp_enabled=config.mcp_enabled,
        mcp_feature_enabled=_mcp_feature_enabled(definition.system),
        mcp_enabled_operations=config.mcp_enabled_operations,
        mcp_disabled_operations=config.mcp_disabled_operations,
        health_status=config.health_status,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
    )


@router.post("/connectors/{connector_id}/disable", response_model=ConnectorConfigResponse)
async def disable_connector(connector_id: str, http_request: Request) -> ConnectorConfigResponse:
    """
    Disable a connector.
    """
    store = get_config_store()
    config = store.get(connector_id)
    definition = get_connector_definition(connector_id)
    mcp_feature_enabled = _mcp_feature_enabled(definition.system) if definition else True

    if not config:
        raise HTTPException(
            status_code=404, detail=f"Connector configuration not found: {connector_id}"
        )

    config.enabled = False
    config.updated_at = datetime.now(timezone.utc)
    store.save(config)

    auth = http_request.state.auth
    get_audit_log_store().record_event(
        build_event(
            tenant_id=auth.tenant_id,
            actor_id=auth.subject,
            actor_type="user",
            roles=auth.roles,
            action="connector.disabled",
            resource_type="connector",
            resource_id=connector_id,
            outcome="success",
        )
    )

    return ConnectorConfigResponse(
        connector_id=config.connector_id,
        name=config.name,
        category=config.category.value,
        enabled=config.enabled,
        sync_direction=config.sync_direction.value,
        sync_frequency=config.sync_frequency.value,
        instance_url=config.instance_url,
        project_key=config.project_key,
        custom_fields=config.custom_fields,
        mcp_server_url=config.mcp_server_url,
        mcp_server_id=config.mcp_server_id,
        mcp_client_id=config.mcp_client_id,
        mcp_client_secret=config.mcp_client_secret,
        mcp_scope=config.mcp_scope,
        mcp_scopes=config.mcp_scopes,
        mcp_api_key=config.mcp_api_key,
        mcp_api_key_header=config.mcp_api_key_header,
        mcp_oauth_token=config.mcp_oauth_token,
        client_id=config.client_id,
        client_secret=config.client_secret,
        scope=config.scope,
        mcp_tools=config.mcp_tools or list(config.mcp_tool_map.keys()),
        mcp_tool_map=config.mcp_tool_map,
        prefer_mcp=config.prefer_mcp,
        mcp_enabled=config.mcp_enabled,
        mcp_feature_enabled=mcp_feature_enabled,
        mcp_enabled_operations=config.mcp_enabled_operations,
        mcp_disabled_operations=config.mcp_disabled_operations,
        health_status=config.health_status,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
    )


@router.post(
    "/projects/{project_id}/connectors/{system}/mcp",
    response_model=ProjectMcpConfigResponse,
)
async def enable_project_mcp_config(
    project_id: str, system: str, request: ProjectMcpConfigRequest
) -> ProjectMcpConfigResponse:
    """
    Enable MCP configuration for a project-scoped connector.
    """
    definition = _get_mcp_definition_by_system(system)
    _ensure_connector_is_available(definition)

    store = get_project_config_store()
    existing = store.get(project_id, definition.connector_id)
    now = datetime.now(timezone.utc)

    if existing:
        config = existing
        config.mcp_server_url = str(request.mcp_server_url)
        config.mcp_server_id = request.mcp_server_id or definition.mcp_server_id or system
        config.mcp_tool_map = request.mcp_tool_map
        config.mcp_tools = list(request.mcp_tool_map.keys())
        config.updated_at = now
    else:
        config = ProjectConnectorConfig(
            ppm_project_id=project_id,
            connector_id=definition.connector_id,
            name=definition.name,
            category=definition.category,
            mcp_server_url=str(request.mcp_server_url),
            mcp_server_id=request.mcp_server_id or definition.mcp_server_id or system,
            mcp_tool_map=request.mcp_tool_map,
            mcp_tools=list(request.mcp_tool_map.keys()),
            created_at=now,
            updated_at=now,
        )

    store.save(config)
    store.enable_connector(project_id, definition.connector_id)
    updated = store.get(project_id, definition.connector_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Unable to enable MCP configuration")
    return _build_project_mcp_response(project_id, updated)


@router.put(
    "/projects/{project_id}/connectors/{system}/mcp",
    response_model=ProjectMcpConfigResponse,
)
async def update_project_mcp_config(
    project_id: str, system: str, request: ProjectMcpConfigRequest
) -> ProjectMcpConfigResponse:
    """
    Update MCP configuration for a project-scoped connector.
    """
    definition = _get_mcp_definition_by_system(system)
    _ensure_connector_is_available(definition)

    store = get_project_config_store()
    existing = store.get(project_id, definition.connector_id)
    now = datetime.now(timezone.utc)

    if existing:
        config = existing
        config.mcp_server_url = str(request.mcp_server_url)
        config.mcp_server_id = request.mcp_server_id or definition.mcp_server_id or system
        config.mcp_tool_map = request.mcp_tool_map
        config.mcp_tools = list(request.mcp_tool_map.keys())
        config.updated_at = now
    else:
        config = ProjectConnectorConfig(
            ppm_project_id=project_id,
            connector_id=definition.connector_id,
            name=definition.name,
            category=definition.category,
            enabled=False,
            mcp_server_url=str(request.mcp_server_url),
            mcp_server_id=request.mcp_server_id or definition.mcp_server_id or system,
            mcp_tool_map=request.mcp_tool_map,
            mcp_tools=list(request.mcp_tool_map.keys()),
            created_at=now,
            updated_at=now,
        )

    store.save(config)
    updated = store.get(project_id, definition.connector_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Unable to update MCP configuration")
    return _build_project_mcp_response(project_id, updated)


@router.post(
    "/projects/{project_id}/connectors/{connector_id}/enable",
    response_model=ProjectConnectorConfigResponse,
)
async def enable_project_connector(
    project_id: str, connector_id: str
) -> ProjectConnectorConfigResponse:
    """
    Enable a project-scoped connector.
    """
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    _ensure_connector_is_available(definition)

    store = get_project_config_store()
    config = store.get(project_id, connector_id)
    if not config:
        config = ProjectConnectorConfig(
            ppm_project_id=project_id,
            connector_id=connector_id,
            name=definition.name,
            category=definition.category,
        )
        store.save(config)

    store.enable_connector(project_id, connector_id)
    config = store.get(project_id, connector_id)

    return ProjectConnectorConfigResponse(
        connector_id=config.connector_id,
        project_id=config.ppm_project_id,
        name=config.name,
        category=config.category.value,
        enabled=config.enabled,
        sync_direction=config.sync_direction.value,
        sync_frequency=config.sync_frequency.value,
        instance_url=config.instance_url,
        project_key=config.project_key,
        custom_fields=config.custom_fields,
        mcp_server_url=config.mcp_server_url,
        mcp_server_id=config.mcp_server_id,
        mcp_client_id=config.mcp_client_id,
        mcp_client_secret=config.mcp_client_secret,
        mcp_scope=config.mcp_scope,
        mcp_scopes=config.mcp_scopes,
        mcp_api_key=config.mcp_api_key,
        mcp_api_key_header=config.mcp_api_key_header,
        mcp_oauth_token=config.mcp_oauth_token,
        client_id=config.client_id,
        client_secret=config.client_secret,
        scope=config.scope,
        mcp_tools=config.mcp_tools or list(config.mcp_tool_map.keys()),
        mcp_tool_map=config.mcp_tool_map,
        prefer_mcp=config.prefer_mcp,
        mcp_enabled=config.mcp_enabled,
        mcp_feature_enabled=_mcp_feature_enabled(definition.system, project_id),
        mcp_enabled_operations=config.mcp_enabled_operations,
        mcp_disabled_operations=config.mcp_disabled_operations,
        health_status=config.health_status,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
    )


@router.post(
    "/projects/{project_id}/connectors/{connector_id}/disable",
    response_model=ProjectConnectorConfigResponse,
)
async def disable_project_connector(
    project_id: str, connector_id: str
) -> ProjectConnectorConfigResponse:
    """
    Disable a project-scoped connector.
    """
    store = get_project_config_store()
    config = store.get(project_id, connector_id)
    definition = get_connector_definition(connector_id)
    mcp_feature_enabled = (
        _mcp_feature_enabled(definition.system, project_id) if definition else True
    )
    if not config:
        raise HTTPException(
            status_code=404, detail=f"Connector configuration not found: {connector_id}"
        )

    config.enabled = False
    config.updated_at = datetime.now(timezone.utc)
    store.save(config)

    return ProjectConnectorConfigResponse(
        connector_id=config.connector_id,
        project_id=config.ppm_project_id,
        name=config.name,
        category=config.category.value,
        enabled=config.enabled,
        sync_direction=config.sync_direction.value,
        sync_frequency=config.sync_frequency.value,
        instance_url=config.instance_url,
        project_key=config.project_key,
        custom_fields=config.custom_fields,
        mcp_server_url=config.mcp_server_url,
        mcp_server_id=config.mcp_server_id,
        mcp_client_id=config.mcp_client_id,
        mcp_client_secret=config.mcp_client_secret,
        mcp_scope=config.mcp_scope,
        mcp_scopes=config.mcp_scopes,
        mcp_api_key=config.mcp_api_key,
        mcp_api_key_header=config.mcp_api_key_header,
        mcp_oauth_token=config.mcp_oauth_token,
        client_id=config.client_id,
        client_secret=config.client_secret,
        scope=config.scope,
        mcp_tools=config.mcp_tools or list(config.mcp_tool_map.keys()),
        mcp_tool_map=config.mcp_tool_map,
        prefer_mcp=config.prefer_mcp,
        mcp_enabled=config.mcp_enabled,
        mcp_feature_enabled=mcp_feature_enabled,
        mcp_enabled_operations=config.mcp_enabled_operations,
        mcp_disabled_operations=config.mcp_disabled_operations,
        health_status=config.health_status,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
    )


@router.post("/connectors/{connector_id}/test", response_model=TestConnectionResponse)
async def test_connection(
    connector_id: str, request: TestConnectionRequest
) -> TestConnectionResponse:
    """
    Test connection to the external system.

    For Jira connector, requires environment variables:
    - JIRA_INSTANCE_URL (or use request.instance_url)
    - JIRA_EMAIL
    - JIRA_API_TOKEN
    """
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    _ensure_connector_is_available(definition)

    store = get_config_store()
    config = store.get(connector_id)

    # Create config with request values
    test_config = ConnectorConfig(
        connector_id=connector_id,
        name=definition.name,
        category=definition.category,
        instance_url=request.instance_url or (config.instance_url if config else ""),
        project_key=request.project_key or (config.project_key if config else ""),
        mcp_server_url=config.mcp_server_url if config else "",
        mcp_server_id=config.mcp_server_id if config else "",
        mcp_client_id=config.mcp_client_id if config else "",
        mcp_client_secret=config.mcp_client_secret if config else "",
        mcp_scope=config.mcp_scope if config else "",
        mcp_api_key=config.mcp_api_key if config else "",
        mcp_api_key_header=config.mcp_api_key_header if config else "",
        mcp_oauth_token=config.mcp_oauth_token if config else "",
        mcp_tool_map=config.mcp_tool_map if config else {},
        prefer_mcp=config.prefer_mcp if config else False,
        mcp_enabled=config.mcp_enabled if config else True,
        mcp_enabled_operations=config.mcp_enabled_operations if config else [],
        mcp_disabled_operations=config.mcp_disabled_operations if config else [],
    )

    handler_type, handler = get_test_connection_handler(connector_id, config=test_config)
    if not handler:
        return TestConnectionResponse(
            status=ConnectionStatus.FAILED.value,
            message=f"Connection testing is not supported for connector '{connector_id}'.",
            details={"connector_id": connector_id, "reason": "unsupported"},
            tested_at=datetime.now(timezone.utc).isoformat(),
        )

    circuit_breaker = get_circuit_breaker()
    if not circuit_breaker.allow_request(connector_id):
        return TestConnectionResponse(
            status="circuit_open",
            message="Connector circuit is open; skipping test and returning fallback response.",
            details={"connector_id": connector_id},
            tested_at=datetime.now(timezone.utc).isoformat(),
        )

    try:
        if handler_type == "class":
            connector = handler(test_config)
            result = connector.test_connection()
        else:
            result = handler(test_config)
    except (ConnectionError, RuntimeError, TimeoutError, TypeError, ValueError) as exc:
        circuit_breaker.record_failure(connector_id)
        raise HTTPException(
            status_code=502,
            detail=f"Connector test failed: {connector_id}",
        ) from exc
    else:
        if result.status == ConnectionStatus.CONNECTED:
            circuit_breaker.record_success(connector_id)
        else:
            circuit_breaker.record_failure(connector_id)

    # Update health status in stored config
    if config:
        config.health_status = (
            "healthy" if result.status == ConnectionStatus.CONNECTED else "unhealthy"
        )
        config.updated_at = datetime.now(timezone.utc)
        store.save(config)

    return TestConnectionResponse(
        status=result.status.value,
        message=result.message,
        details=result.details,
        tested_at=result.tested_at.isoformat(),
    )


@router.post("/connectors/regulatory_compliance/test", response_model=TestConnectionResponse)
async def test_regulatory_compliance_connection(
    request: RegulatoryComplianceConfigRequest,
) -> TestConnectionResponse:
    connector_id = "regulatory_compliance"
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    store = get_config_store()
    existing = store.get(connector_id)
    custom_fields = dict(existing.custom_fields) if existing else {}
    if request.endpoint_url:
        custom_fields["endpoint_url"] = request.endpoint_url
    if request.api_key:
        custom_fields["api_key"] = request.api_key
    if request.supported_regulations:
        custom_fields["supported_regulations"] = request.supported_regulations

    test_config = ConnectorConfig(
        connector_id=connector_id,
        name=definition.name,
        category=definition.category,
        instance_url=request.endpoint_url or (existing.instance_url if existing else ""),
        custom_fields=custom_fields,
    )

    connector = RegulatoryComplianceConnector(test_config)
    result = connector.test_connection()

    if existing:
        existing.health_status = (
            "healthy" if result.status == ConnectionStatus.CONNECTED else "unhealthy"
        )
        existing.updated_at = datetime.now(timezone.utc)
        store.save(existing)

    return TestConnectionResponse(
        status=result.status.value,
        message=result.message,
        details=result.details,
        tested_at=result.tested_at.isoformat(),
    )


@router.get("/connectors/regulatory_compliance/audit-logs")
async def get_regulatory_audit_logs(
    regulation: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    connector_id = "regulatory_compliance"
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    store = get_config_store()
    config = store.get(connector_id)
    if not config:
        raise HTTPException(
            status_code=404, detail=f"Connector configuration not found: {connector_id}"
        )

    connector = RegulatoryComplianceConnector(config)
    filters = {"regulation": regulation} if regulation else None
    items = connector.read("audit_logs", filters=filters, limit=limit, offset=offset)
    return {"items": items, "count": len(items)}


@router.post("/connectors/{connector_id}/webhook")
async def handle_connector_webhook(connector_id: str, request: Request) -> dict[str, Any]:
    """
    Receive webhook notifications from external systems.
    """
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    config = get_config_store().get(connector_id)
    if not config or not config.enabled:
        raise HTTPException(status_code=403, detail="Connector not enabled")

    handler = get_webhook_handler(connector_id)
    if not handler:
        raise HTTPException(status_code=404, detail="Webhook handler not registered")

    circuit_breaker = get_circuit_breaker()
    if not circuit_breaker.allow_request(connector_id):
        return {
            "status": "circuit_open",
            "message": "Connector circuit is open; webhook buffered for later processing.",
            "connector_id": connector_id,
        }

    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    _validate_webhook_signature(connector_id, body, headers)
    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    try:
        result = handler(payload, headers)
    except (ConnectionError, RuntimeError, TimeoutError, TypeError, ValueError) as exc:
        circuit_breaker.record_failure(connector_id)
        raise HTTPException(status_code=502, detail="Connector webhook processing failed") from exc
    else:
        circuit_breaker.record_success(connector_id)
    tenant_id = request.headers.get("X-Tenant-ID")
    sanitized_headers = _sanitize_headers(headers)
    get_webhook_store().record_event(
        WebhookEvent.from_payload(
            connector_id=connector_id,
            payload=payload,
            headers=sanitized_headers,
            result=result if isinstance(result, dict) else {"result": result},
            tenant_id=tenant_id,
        )
    )
    if tenant_id:
        get_audit_log_store().record_event(
            build_event(
                tenant_id=tenant_id,
                actor_id="webhook",
                actor_type="system",
                roles=["system"],
                action="connector.webhook.received",
                resource_type="connector",
                resource_id=connector_id,
                outcome="success",
                metadata={"connector_id": connector_id},
            )
        )
    return {"status": "received", "connector_id": connector_id, "result": result}


@router.delete("/connectors/{connector_id}/config")
async def delete_connector_config(connector_id: str, http_request: Request) -> dict[str, str]:
    """
    Delete a connector configuration.
    """
    store = get_config_store()
    if not store.delete(connector_id):
        raise HTTPException(
            status_code=404, detail=f"Connector configuration not found: {connector_id}"
        )

    auth = http_request.state.auth
    get_audit_log_store().record_event(
        build_event(
            tenant_id=auth.tenant_id,
            actor_id=auth.subject,
            actor_type="user",
            roles=auth.roles,
            action="connector.config.deleted",
            resource_type="connector",
            resource_id=connector_id,
            outcome="success",
        )
    )

    return {"status": "deleted", "connector_id": connector_id}
