"""
Connector API Routes

Provides endpoints for connector management:
- List available connectors
- Get/update connector configurations
- Test connector connections
- Enable/disable connectors with mutual exclusivity
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

# Add connector SDK to path
REPO_ROOT = Path(__file__).resolve().parents[5]
CONNECTOR_SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
JIRA_CONNECTOR_PATH = REPO_ROOT / "connectors" / "jira" / "src"
for path in (CONNECTOR_SDK_PATH, JIRA_CONNECTOR_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from base_connector import (
    ConnectorCategory,
    ConnectorConfig,
    ConnectorConfigStore,
    ConnectionStatus,
    SyncDirection,
    SyncFrequency,
)
from connector_registry import (
    ConnectorStatus,
    get_all_connectors,
    get_connector_definition,
    get_connectors_by_category,
)
from security.audit_log import build_event, get_audit_log_store

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize connector config store
# In production, this path should come from environment
_config_store: ConnectorConfigStore | None = None


def get_config_store() -> ConnectorConfigStore:
    """Get or create the connector config store."""
    global _config_store
    if _config_store is None:
        storage_path = REPO_ROOT / "data" / "connectors" / "config.json"
        _config_store = ConnectorConfigStore(storage_path)
    return _config_store


# =============================================================================
# Request/Response Models
# =============================================================================


class ConnectorDefinitionResponse(BaseModel):
    """Response model for connector definition."""

    connector_id: str
    name: str
    description: str
    category: str
    status: str
    icon: str
    supported_sync_directions: list[str]
    auth_type: str
    config_fields: list[dict[str, Any]]
    env_vars: list[str]


class ConnectorConfigRequest(BaseModel):
    """Request model for creating/updating connector configuration."""

    instance_url: str = ""
    project_key: str = ""
    sync_direction: str = Field(default="inbound", pattern="^(inbound|outbound|bidirectional)$")
    sync_frequency: str = Field(
        default="daily",
        pattern="^(realtime|hourly|every_4_hours|daily|weekly|manual)$",
    )
    custom_fields: dict[str, Any] = Field(default_factory=dict)


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
    health_status: str
    created_at: str
    updated_at: str
    last_sync_at: str | None


class ConnectorListItemResponse(BaseModel):
    """Response model for connector list items (combines definition and config)."""

    # Definition fields
    connector_id: str
    name: str
    description: str
    category: str
    status: str  # available, coming_soon, beta
    icon: str
    supported_sync_directions: list[str]
    auth_type: str
    config_fields: list[dict[str, Any]]
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


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/connectors/categories", response_model=list[CategoryInfo])
async def list_categories():
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

    return categories


@router.get("/connectors", response_model=list[ConnectorListItemResponse])
async def list_connectors(category: str | None = None):
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
            status=definition.status.value,
            icon=definition.icon,
            supported_sync_directions=[d.value for d in definition.supported_sync_directions],
            auth_type=definition.auth_type,
            config_fields=definition.config_fields,
            env_vars=definition.env_vars,
            enabled=config.enabled if config else False,
            configured=config is not None,
            instance_url=config.instance_url if config else "",
            project_key=config.project_key if config else "",
            sync_direction=config.sync_direction.value if config else "inbound",
            sync_frequency=config.sync_frequency.value if config else "daily",
            health_status=config.health_status if config else "unknown",
            last_sync_at=config.last_sync_at.isoformat() if config and config.last_sync_at else None,
        )
        result.append(item)

    return result


@router.get("/connectors/{connector_id}", response_model=ConnectorListItemResponse)
async def get_connector(connector_id: str):
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
        status=definition.status.value,
        icon=definition.icon,
        supported_sync_directions=[d.value for d in definition.supported_sync_directions],
        auth_type=definition.auth_type,
        config_fields=definition.config_fields,
        env_vars=definition.env_vars,
        enabled=config.enabled if config else False,
        configured=config is not None,
        instance_url=config.instance_url if config else "",
        project_key=config.project_key if config else "",
        sync_direction=config.sync_direction.value if config else "inbound",
        sync_frequency=config.sync_frequency.value if config else "daily",
        health_status=config.health_status if config else "unknown",
        last_sync_at=config.last_sync_at.isoformat() if config and config.last_sync_at else None,
    )


@router.put("/connectors/{connector_id}/config", response_model=ConnectorConfigResponse)
async def update_connector_config(
    connector_id: str, request: ConnectorConfigRequest, http_request: Request
):
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
        health_status=config.health_status,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
    )


@router.post("/connectors/{connector_id}/enable", response_model=ConnectorConfigResponse)
async def enable_connector(connector_id: str, http_request: Request):
    """
    Enable a connector.

    This will disable any other connector in the same category (mutual exclusivity).
    """
    definition = get_connector_definition(connector_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    if definition.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Connector '{connector_id}' is not yet available (status: {definition.status.value})",
        )

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
        health_status=config.health_status,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
    )


@router.post("/connectors/{connector_id}/disable", response_model=ConnectorConfigResponse)
async def disable_connector(connector_id: str, http_request: Request):
    """
    Disable a connector.
    """
    store = get_config_store()
    config = store.get(connector_id)

    if not config:
        raise HTTPException(status_code=404, detail=f"Connector configuration not found: {connector_id}")

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
        health_status=config.health_status,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
    )


@router.post("/connectors/{connector_id}/test", response_model=TestConnectionResponse)
async def test_connection(connector_id: str, request: TestConnectionRequest):
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

    if definition.status != ConnectorStatus.AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Connection testing is not available for connector '{connector_id}' (status: {definition.status.value})",
        )

    store = get_config_store()
    config = store.get(connector_id)

    # Create config with request values
    test_config = ConnectorConfig(
        connector_id=connector_id,
        name=definition.name,
        category=definition.category,
        instance_url=request.instance_url or (config.instance_url if config else ""),
        project_key=request.project_key or (config.project_key if config else ""),
    )

    # Currently only Jira is implemented
    if connector_id == "jira":
        from jira_connector import JiraConnector

        connector = JiraConnector(test_config)
        result = connector.test_connection()

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
    else:
        # Stub for other connectors
        raise HTTPException(
            status_code=501,
            detail=f"Connection testing not implemented for connector: {connector_id}",
        )


@router.delete("/connectors/{connector_id}/config")
async def delete_connector_config(connector_id: str, http_request: Request):
    """
    Delete a connector configuration.
    """
    store = get_config_store()
    if not store.delete(connector_id):
        raise HTTPException(status_code=404, detail=f"Connector configuration not found: {connector_id}")

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
