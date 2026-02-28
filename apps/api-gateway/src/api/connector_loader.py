from __future__ import annotations

import importlib
from typing import Any

from feature_flags import is_mcp_feature_enabled

from connectors.sdk.src.base_connector import ConnectorConfig
from connectors.sdk.src.connector_registry import (
    get_all_connectors,
    get_connector_definition,
)
from connectors.sdk.src.project_connector_store import ProjectConnectorConfig

_CONNECTOR_CLASS_MAP: dict[str, tuple[str, str]] = {
    "jira": ("jira_connector", "JiraConnector"),
    "jira_mcp": ("jira_connector", "JiraConnector"),
    "planview": ("planview_connector", "PlanviewConnector"),
    "planview_mcp": ("planview_connector", "PlanviewConnector"),
    "clarity": ("clarity_connector", "ClarityConnector"),
    "clarity_mcp": ("clarity_connector", "ClarityConnector"),
    "ms_project_server": ("ms_project_server_connector", "MsProjectServerConnector"),
    "azure_devops": ("azure_devops_connector", "AzureDevOpsConnector"),
    "monday": ("monday_connector", "MondayConnector"),
    "asana": ("asana_connector", "AsanaConnector"),
    "asana_mcp": ("asana_connector", "AsanaConnector"),
    "sharepoint": ("sharepoint_connector", "SharePointConnector"),
    "confluence": ("confluence_connector", "ConfluenceConnector"),
    "google_drive": ("google_drive_connector", "GoogleDriveConnector"),
    "sap": ("sap_connector", "SapConnector"),
    "sap_mcp": ("sap_connector", "SapConnector"),
    "oracle": ("oracle_connector", "OracleConnector"),
    "netsuite": ("netsuite_connector", "NetSuiteConnector"),
    "workday": ("workday_connector", "WorkdayConnector"),
    "workday_mcp": ("workday_connector", "WorkdayConnector"),
    "sap_successfactors": ("sap_successfactors_connector", "SapSuccessFactorsConnector"),
    "adp": ("adp_connector", "AdpConnector"),
    "teams": ("teams_connector", "TeamsConnector"),
    "teams_mcp": ("teams_connector", "TeamsConnector"),
    "slack": ("slack_connector", "SlackConnector"),
    "slack_mcp": ("slack_connector", "SlackConnector"),
    "zoom": ("zoom_connector", "ZoomConnector"),
    "servicenow_grc": ("servicenow_grc_connector", "ServiceNowGrcConnector"),
    "archer": ("archer_connector", "ArcherConnector"),
    "logicgate": ("logicgate_connector", "LogicGateConnector"),
    "regulatory_compliance": (
        "regulatory_compliance_connector",
        "RegulatoryComplianceConnector",
    ),
    "iot": ("iot_connector", "IoTConnector"),
}

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
    module = importlib.import_module(module_name)
    return getattr(module, class_name, None)
