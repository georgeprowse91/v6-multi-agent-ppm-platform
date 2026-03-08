"""
Connector Registry — dynamically loads connector definitions from manifest.yaml files.

Each connector's manifest.yaml is the **single source of truth** for its identity,
capabilities, configuration, and maturity.  This module discovers all manifests at
import time and exposes them via a stable Python API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

from base_connector import ConnectorCategory, SyncDirection  # noqa: E402
from runtime_flags import demo_mode_enabled  # noqa: E402

logger = logging.getLogger(__name__)

CONNECTORS_ROOT = REPO_ROOT / "connectors"

# ---------------------------------------------------------------------------
# Enums & dataclass  (public API — unchanged from previous version)
# ---------------------------------------------------------------------------


class ConnectorStatus(str, Enum):
    """Implementation status of a connector."""

    AVAILABLE = "available"
    COMING_SOON = "coming_soon"
    BETA = "beta"


@dataclass
class ConnectorDefinition:
    """Definition of an available connector."""

    connector_id: str
    name: str
    description: str
    category: ConnectorCategory
    system: str = ""
    mcp_server_id: str = ""
    mcp_server_url: str = ""
    supported_operations: list[str] = field(default_factory=list)
    tool_map: dict[str, str] = field(default_factory=dict)
    prefer_mcp: bool = False
    status: ConnectorStatus = ConnectorStatus.COMING_SOON
    icon: str = ""
    supported_sync_directions: list[SyncDirection] = field(
        default_factory=lambda: [SyncDirection.INBOUND]
    )
    auth_type: str = "api_key"
    config_fields: list[dict[str, Any]] = field(default_factory=list)
    config_schema: list[dict[str, Any]] | None = None
    env_vars: list[str] = field(default_factory=list)
    supported_objects: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    auth_requirements: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.system:
            self.system = self.connector_id
        if self.config_schema is None:
            self.config_schema = list(self.config_fields)

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "system": self.system,
            "mcp_server_id": self.mcp_server_id,
            "mcp_server_url": self.mcp_server_url,
            "supported_operations": self.supported_operations,
            "tool_map": self.tool_map,
            "prefer_mcp": self.prefer_mcp,
            "status": self.status.value,
            "icon": self.icon,
            "supported_sync_directions": [d.value for d in self.supported_sync_directions],
            "auth_type": self.auth_type,
            "config_fields": self.config_fields,
            "config_schema": self.config_schema or self.config_fields,
            "env_vars": self.env_vars,
            "supported_objects": self.supported_objects,
            "limitations": self.limitations,
            "auth_requirements": self.auth_requirements,
        }


# ---------------------------------------------------------------------------
# Shared field templates (re-exported for callers that reference them)
# ---------------------------------------------------------------------------

OAUTH_ROTATION_FIELDS: list[dict[str, Any]] = [
    {"name": "rotation_enabled", "type": "boolean", "required": False, "label": "Enable secret rotation"},
    {"name": "rotation_provider", "type": "string", "required": False, "label": "Rotation provider (azure_automation or background_job)"},
    {"name": "refresh_token_rotation_days", "type": "number", "required": False, "label": "Refresh token rotation (days)"},
    {"name": "client_secret_rotation_days", "type": "number", "required": False, "label": "Client secret rotation (days)"},
]

MCP_CONFIG_FIELDS: list[dict[str, Any]] = [
    {"name": "mcp_server_url", "type": "url", "required": True, "label": "MCP Server URL"},
    {"name": "mcp_scopes", "type": "array", "required": False, "label": "MCP Scopes"},
    {"name": "tool_map", "type": "object", "required": False, "label": "MCP Tool Map"},
]

# ---------------------------------------------------------------------------
# Manifest → ConnectorDefinition mapping
# ---------------------------------------------------------------------------

_CATEGORY_MAP: dict[str, ConnectorCategory] = {
    "ppm": ConnectorCategory.PPM,
    "project-portfolio-management": ConnectorCategory.PPM,
    "work-management": ConnectorCategory.PM,
    "pm": ConnectorCategory.PM,
    "devops": ConnectorCategory.PM,
    "doc_mgmt": ConnectorCategory.DOC_MGMT,
    "document-management": ConnectorCategory.DOC_MGMT,
    "erp": ConnectorCategory.ERP,
    "hris": ConnectorCategory.HRIS,
    "collaboration": ConnectorCategory.COLLABORATION,
    "grc": ConnectorCategory.GRC,
    "it-service": ConnectorCategory.GRC,
    "compliance": ConnectorCategory.COMPLIANCE,
    "iot": ConnectorCategory.IOT,
    "crm": ConnectorCategory.CRM,
    "mock": ConnectorCategory.PM,
}

_STATUS_MAP: dict[str, ConnectorStatus] = {
    "available": ConnectorStatus.AVAILABLE,
    "production": ConnectorStatus.AVAILABLE,
    "beta": ConnectorStatus.BETA,
    "coming_soon": ConnectorStatus.COMING_SOON,
    "coming-soon": ConnectorStatus.COMING_SOON,
}

_DIRECTION_MAP: dict[str, SyncDirection] = {
    "inbound": SyncDirection.INBOUND,
    "outbound": SyncDirection.OUTBOUND,
    "bidirectional": SyncDirection.BIDIRECTIONAL,
    "bi-directional": SyncDirection.BIDIRECTIONAL,
}


def _parse_manifest(manifest: dict[str, Any]) -> ConnectorDefinition | None:
    """Convert a parsed manifest.yaml dict into a ConnectorDefinition."""
    connector_id = manifest.get("id")
    if not connector_id:
        return None

    category_str = str(manifest.get("category", "")).lower()
    category = _CATEGORY_MAP.get(category_str)
    if category is None:
        logger.warning("Unknown connector category %r for %s", category_str, connector_id)
        return None

    # Status
    status_str = str(manifest.get("status", "coming_soon")).lower()
    status = _STATUS_MAP.get(status_str, ConnectorStatus.COMING_SOON)

    # Auth type — trust auth.type from the manifest.  Only override to "mcp"
    # for pure MCP connectors (prefer_mcp=true) that don't have their own auth.
    auth = manifest.get("auth") or {}
    auth_type = auth.get("type", "api_key")
    if manifest.get("prefer_mcp") and manifest.get("protocol") == "mcp":
        auth_type = "mcp"

    # Sync directions
    sync_section = manifest.get("sync") or {}
    raw_directions = sync_section.get("directions", [])
    directions = [_DIRECTION_MAP[d] for d in raw_directions if d in _DIRECTION_MAP]
    if not directions:
        directions = [SyncDirection.INBOUND]

    # MCP fields
    mcp_section = manifest.get("mcp") or {}
    mcp_server_id = mcp_section.get("server_id", "") or manifest.get("mcp_server_id", "")
    mcp_server_url = mcp_section.get("server_url", "") or manifest.get("mcp_server_url", "")
    tool_map = mcp_section.get("tool_map") or manifest.get("tool_map") or {}
    if isinstance(tool_map, str):
        tool_map = {}

    # Config fields — auto-append OAuth rotation fields for oauth2 connectors
    config_fields = list(manifest.get("config_fields") or [])
    if auth_type == "oauth2":
        existing_names = {f.get("name") for f in config_fields}
        for rotation_field in OAUTH_ROTATION_FIELDS:
            if rotation_field["name"] not in existing_names:
                config_fields.append(rotation_field)

    return ConnectorDefinition(
        connector_id=connector_id,
        name=manifest.get("name", connector_id),
        description=manifest.get("description", ""),
        category=category,
        system=manifest.get("system", ""),
        mcp_server_id=mcp_server_id,
        mcp_server_url=mcp_server_url,
        supported_operations=manifest.get("supported_operations") or [],
        tool_map=tool_map,
        prefer_mcp=bool(manifest.get("prefer_mcp", False)),
        status=status,
        icon=manifest.get("icon", ""),
        supported_sync_directions=directions,
        auth_type=auth_type,
        config_fields=config_fields,
        env_vars=manifest.get("env_vars") or [],
    )


# ---------------------------------------------------------------------------
# Discovery — find and load all connector manifests
# ---------------------------------------------------------------------------

def _discover_connectors() -> list[ConnectorDefinition]:
    """Scan connectors/*/manifest.yaml and build ConnectorDefinition list."""
    connectors: list[ConnectorDefinition] = []

    for manifest_path in sorted(CONNECTORS_ROOT.glob("*/manifest.yaml")):
        # Skip mock connectors (they live under connectors/mock/*)
        if manifest_path.parent.parent.name == "mock":
            continue
        try:
            data = yaml.safe_load(manifest_path.read_text()) or {}
        except (OSError, yaml.YAMLError) as exc:
            logger.warning("Failed to load %s: %s", manifest_path, exc)
            continue

        definition = _parse_manifest(data)
        if definition is not None:
            connectors.append(definition)

    return connectors


# ---------------------------------------------------------------------------
# Registry (populated at import time)
# ---------------------------------------------------------------------------

ALL_CONNECTORS: list[ConnectorDefinition] = _discover_connectors()

CONNECTORS_BY_ID: dict[str, ConnectorDefinition] = {c.connector_id: c for c in ALL_CONNECTORS}

CONNECTORS_BY_CATEGORY: dict[ConnectorCategory, list[ConnectorDefinition]] = {}
for _connector in ALL_CONNECTORS:
    CONNECTORS_BY_CATEGORY.setdefault(_connector.category, []).append(_connector)


# ---------------------------------------------------------------------------
# Demo mode overrides  (same mechanism as before)
# ---------------------------------------------------------------------------

DEMO_CONNECTOR_CONFIG_ROOT = REPO_ROOT / "ops" / "config" / "connectors" / "mock"


def _load_demo_overrides() -> dict[str, dict[str, Any]]:
    overrides: dict[str, dict[str, Any]] = {}
    if not DEMO_CONNECTOR_CONFIG_ROOT.exists():
        return overrides

    for config_file in DEMO_CONNECTOR_CONFIG_ROOT.glob("*.yaml"):
        payload = yaml.safe_load(config_file.read_text()) or {}
        connector_id = payload.get("connector_id")
        if not connector_id:
            continue
        normalized_connector_id = "servicenow_grc" if connector_id == "servicenow" else connector_id
        connector = CONNECTORS_BY_ID.get(normalized_connector_id)
        if connector is None:
            continue
        overrides[normalized_connector_id] = {
            "auth_type": payload.get("auth_type", "none"),
            "status": ConnectorStatus.AVAILABLE,
            "description": f"{connector.description} (mock demo mode)",
        }
    return overrides


def _apply_demo_overrides() -> None:
    if not demo_mode_enabled():
        return
    for connector_id, overrides in _load_demo_overrides().items():
        connector = CONNECTORS_BY_ID.get(connector_id)
        if connector is None:
            continue
        for field_name, value in overrides.items():
            setattr(connector, field_name, value)


# ---------------------------------------------------------------------------
# Public API  (unchanged signatures for backwards compatibility)
# ---------------------------------------------------------------------------

def get_connector_definition(connector_id: str) -> ConnectorDefinition | None:
    """Get a connector definition by ID."""
    _apply_demo_overrides()
    return CONNECTORS_BY_ID.get(connector_id)


def get_connectors_by_category(category: ConnectorCategory) -> list[ConnectorDefinition]:
    """Get all connectors in a category."""
    _apply_demo_overrides()
    return CONNECTORS_BY_CATEGORY.get(category, [])


def get_all_connectors() -> list[ConnectorDefinition]:
    """Get all connector definitions."""
    _apply_demo_overrides()
    return ALL_CONNECTORS


def get_available_connectors() -> list[ConnectorDefinition]:
    """Get all fully implemented connectors."""
    _apply_demo_overrides()
    return [c for c in ALL_CONNECTORS if c.status == ConnectorStatus.AVAILABLE]
