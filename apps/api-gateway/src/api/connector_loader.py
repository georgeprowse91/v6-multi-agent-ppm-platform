from __future__ import annotations

import importlib
import logging
from typing import Any

from feature_flags import is_mcp_feature_enabled

from connectors.sdk.src.base_connector import ConnectorConfig
from connectors.sdk.src.connector_registry import (
    get_all_connectors,
    get_connector_definition,
)
from connectors.sdk.src.project_connector_store import ProjectConnectorConfig

logger = logging.getLogger(__name__)

_PASCAL = {"iot": "IoT", "sharepoint": "SharePoint", "servicenow": "ServiceNow",
           "netsuite": "NetSuite", "logicgate": "LogicGate", "devops": "DevOps",
           "successfactors": "SuccessFactors"}


def _build_class_map() -> dict[str, tuple[str, str]]:
    """Derive connector_id -> (module, class) from manifests.
    MCP connectors share the module/class of their REST counterpart via ``system``."""
    base = {d.system: d.connector_id for d in get_all_connectors() if d.auth_type != "mcp"}
    m: dict[str, tuple[str, str]] = {}
    for d in get_all_connectors():
        bid = base.get(d.system, d.connector_id) if d.auth_type == "mcp" else d.connector_id
        cls = "".join(_PASCAL.get(p, p.capitalize()) for p in bid.split("_")) + "Connector"
        m[d.connector_id] = (f"{bid}_connector", cls)
    return m


_CONNECTOR_CLASS_MAP: dict[str, tuple[str, str]] = _build_class_map()

_MCP_CONNECTOR_BY_SYSTEM = {
    definition.system: definition.connector_id
    for definition in get_all_connectors()
    if definition.auth_type == "mcp"
}


def _connector_system(connector_id: str) -> str:
    definition = get_connector_definition(connector_id)
    return definition.system if definition else connector_id


def _should_use_mcp(config: ConnectorConfig | ProjectConnectorConfig | None) -> bool:
    return bool(
        config
        and config.prefer_mcp
        and config.mcp_server_url
        and config.is_mcp_enabled_for(None)
        and is_mcp_feature_enabled(
            system=_connector_system(config.connector_id),
            project_id=getattr(config, "ppm_project_id", None),
        )
    )


def resolve_connector_id(
    connector_id: str,
    *,
    config: ConnectorConfig | ProjectConnectorConfig | None = None,
) -> str:
    if not _should_use_mcp(config):
        return connector_id
    system = _connector_system(connector_id)
    return _MCP_CONNECTOR_BY_SYSTEM.get(system, connector_id)


def get_connector_class(
    connector_id: str,
    *,
    config: ConnectorConfig | ProjectConnectorConfig | None = None,
) -> type[Any] | None:
    resolved_id = resolve_connector_id(connector_id, config=config)
    module_info = _CONNECTOR_CLASS_MAP.get(resolved_id)
    if not module_info:
        return None
    module_name, class_name = module_info
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        logger.warning("Connector module %s not found for %s", module_name, resolved_id)
        return None
    return getattr(module, class_name, None)
