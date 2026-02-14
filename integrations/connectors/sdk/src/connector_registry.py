"""
Connector Registry

Defines all available connectors in the platform, organized by category.
Connector implementations are available for the listed integrations.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from base_connector import ConnectorCategory, SyncDirection
from runtime_flags import demo_mode_enabled


class ConnectorStatus(str, Enum):
    """Implementation status of a connector."""

    AVAILABLE = "available"  # Fully functional
    COMING_SOON = "coming_soon"
    BETA = "beta"  # In beta testing


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
    icon: str = ""  # Icon identifier for UI
    supported_sync_directions: list[SyncDirection] = field(
        default_factory=lambda: [SyncDirection.INBOUND]
    )
    auth_type: str = "api_key"  # api_key, oauth2, basic
    config_fields: list[dict[str, Any]] = field(default_factory=list)
    config_schema: list[dict[str, Any]] | None = None
    env_vars: list[str] = field(default_factory=list)  # Required environment variables

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
        }


OAUTH_ROTATION_FIELDS: list[dict[str, Any]] = [
    {
        "name": "rotation_enabled",
        "type": "boolean",
        "required": False,
        "label": "Enable secret rotation",
    },
    {
        "name": "rotation_provider",
        "type": "string",
        "required": False,
        "label": "Rotation provider (azure_automation or background_job)",
    },
    {
        "name": "refresh_token_rotation_days",
        "type": "number",
        "required": False,
        "label": "Refresh token rotation (days)",
    },
    {
        "name": "client_secret_rotation_days",
        "type": "number",
        "required": False,
        "label": "Client secret rotation (days)",
    },
]

MCP_CONFIG_FIELDS: list[dict[str, Any]] = [
    {
        "name": "mcp_server_url",
        "type": "url",
        "required": True,
        "label": "MCP Server URL",
    },
    {
        "name": "mcp_scopes",
        "type": "array",
        "required": False,
        "label": "MCP Scopes",
    },
    {
        "name": "tool_map",
        "type": "object",
        "required": False,
        "label": "MCP Tool Map",
    },
]


def _with_rotation_fields(fields: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [*(fields or []), *OAUTH_ROTATION_FIELDS]


# =============================================================================
# CONNECTOR DEFINITIONS
# =============================================================================

# PPM Tools Category
PLANVIEW_CONNECTOR = ConnectorDefinition(
    connector_id="planview",
    name="Planview",
    description="Enterprise PPM platform for portfolio and resource management",
    category=ConnectorCategory.PPM,
    status=ConnectorStatus.AVAILABLE,
    icon="planview",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": True, "label": "Instance URL"},
            {"name": "portfolio_id", "type": "string", "required": False, "label": "Portfolio ID"},
        ]
    ),
    env_vars=[
        "PLANVIEW_INSTANCE_URL",
        "PLANVIEW_CLIENT_ID",
        "PLANVIEW_CLIENT_SECRET",
        "PLANVIEW_REFRESH_TOKEN",
    ],
)

PLANVIEW_MCP_CONNECTOR = ConnectorDefinition(
    connector_id="planview_mcp",
    system="planview",
    name="Planview (MCP)",
    description="Sync portfolio and project data from Planview via an MCP server.",
    category=ConnectorCategory.PPM,
    status=ConnectorStatus.BETA,
    icon="planview",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="mcp",
    mcp_server_id="planview",
    config_fields=MCP_CONFIG_FIELDS,
    supported_operations=["list", "create"],
    prefer_mcp=True,
)

CLARITY_CONNECTOR = ConnectorDefinition(
    connector_id="clarity",
    name="Clarity PPM",
    description="Broadcom Clarity PPM for enterprise project and portfolio management",
    category=ConnectorCategory.PPM,
    status=ConnectorStatus.AVAILABLE,
    icon="clarity",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": True, "label": "Instance URL"},
        ]
    ),
    env_vars=[
        "CLARITY_INSTANCE_URL",
        "CLARITY_CLIENT_ID",
        "CLARITY_CLIENT_SECRET",
        "CLARITY_REFRESH_TOKEN",
    ],
)

CLARITY_MCP_CONNECTOR = ConnectorDefinition(
    connector_id="clarity_mcp",
    system="clarity",
    name="Clarity PPM (MCP)",
    description="Sync Clarity projects and work items via an MCP server.",
    category=ConnectorCategory.PPM,
    status=ConnectorStatus.BETA,
    icon="clarity",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="mcp",
    mcp_server_id="clarity",
    config_fields=MCP_CONFIG_FIELDS,
    supported_operations=["list", "create"],
    prefer_mcp=True,
)

MS_PROJECT_SERVER_CONNECTOR = ConnectorDefinition(
    connector_id="ms_project_server",
    name="Microsoft Project Server",
    description="Microsoft Project Server/Project Online for enterprise project management",
    category=ConnectorCategory.PPM,
    status=ConnectorStatus.AVAILABLE,
    icon="microsoft",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "tenant_id", "type": "string", "required": True, "label": "Azure Tenant ID"},
            {"name": "site_url", "type": "url", "required": True, "label": "Project Web App URL"},
        ]
    ),
    env_vars=[
        "MS_PROJECT_TENANT_ID",
        "MS_PROJECT_SITE_URL",
        "MS_PROJECT_CLIENT_ID",
        "MS_PROJECT_CLIENT_SECRET",
        "MS_PROJECT_REFRESH_TOKEN",
    ],
)

# PM Tools Category
JIRA_CONNECTOR = ConnectorDefinition(
    connector_id="jira",
    name="Jira",
    description="Atlassian Jira for agile project tracking and issue management",
    category=ConnectorCategory.PM,
    status=ConnectorStatus.AVAILABLE,  # Fully implemented
    icon="jira",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="api_key",
    config_fields=[
        {"name": "instance_url", "type": "url", "required": True, "label": "Instance URL"},
        {"name": "project_key", "type": "string", "required": False, "label": "Project Key"},
    ],
    env_vars=["JIRA_INSTANCE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"],
)

JIRA_MCP_CONNECTOR = ConnectorDefinition(
    connector_id="jira_mcp",
    system="jira",
    name="Jira (MCP)",
    description="Sync projects and work items from Jira via an MCP server.",
    category=ConnectorCategory.PM,
    status=ConnectorStatus.BETA,
    icon="jira",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="mcp",
    mcp_server_id="jira",
    config_fields=MCP_CONFIG_FIELDS,
    supported_operations=["list", "create", "update"],
    prefer_mcp=True,
)

AZURE_DEVOPS_CONNECTOR = ConnectorDefinition(
    connector_id="azure_devops",
    name="Azure DevOps",
    description="Microsoft Azure DevOps for source control, CI/CD, and work tracking",
    category=ConnectorCategory.PM,
    status=ConnectorStatus.AVAILABLE,
    icon="azure",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="api_key",
    config_fields=[
        {"name": "organization_url", "type": "url", "required": True, "label": "Organization URL"},
        {"name": "project_name", "type": "string", "required": True, "label": "Project Name"},
    ],
    env_vars=["AZURE_DEVOPS_ORG_URL", "AZURE_DEVOPS_PAT"],
)

MONDAY_CONNECTOR = ConnectorDefinition(
    connector_id="monday",
    name="Monday.com",
    description="Monday.com work management platform",
    category=ConnectorCategory.PM,
    status=ConnectorStatus.AVAILABLE,
    icon="monday",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="api_key",
    config_fields=[
        {"name": "instance_url", "type": "url", "required": False, "label": "API Base URL"},
        {"name": "board_ids", "type": "string", "required": False, "label": "Board IDs (comma-separated)"},
    ],
    env_vars=["MONDAY_API_TOKEN"],
)

ASANA_CONNECTOR = ConnectorDefinition(
    connector_id="asana",
    name="Asana",
    description="Asana project and task management",
    category=ConnectorCategory.PM,
    status=ConnectorStatus.AVAILABLE,
    icon="asana",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": False, "label": "API Base URL"},
            {"name": "workspace_gid", "type": "string", "required": True, "label": "Workspace GID"},
        ]
    ),
    env_vars=["ASANA_ACCESS_TOKEN"],
)

ASANA_MCP_CONNECTOR = ConnectorDefinition(
    connector_id="asana_mcp",
    system="asana",
    name="Asana (MCP)",
    description="Sync Asana projects and tasks via an MCP server.",
    category=ConnectorCategory.PM,
    status=ConnectorStatus.BETA,
    icon="asana",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="mcp",
    mcp_server_id="asana",
    config_fields=MCP_CONFIG_FIELDS,
    supported_operations=["list", "create"],
    prefer_mcp=True,
)
# Document Management Category
SHAREPOINT_CONNECTOR = ConnectorDefinition(
    connector_id="sharepoint",
    name="SharePoint",
    description="Microsoft SharePoint for document management and collaboration",
    category=ConnectorCategory.DOC_MGMT,
    status=ConnectorStatus.AVAILABLE,
    icon="sharepoint",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "site_url", "type": "url", "required": True, "label": "SharePoint Site URL"},
            {
                "name": "document_library",
                "type": "string",
                "required": False,
                "label": "Document Library",
            },
        ]
    ),
    env_vars=[
        "SHAREPOINT_SITE_URL",
        "SHAREPOINT_CLIENT_ID",
        "SHAREPOINT_CLIENT_SECRET",
        "SHAREPOINT_REFRESH_TOKEN",
    ],
)

CONFLUENCE_CONNECTOR = ConnectorDefinition(
    connector_id="confluence",
    name="Confluence",
    description="Atlassian Confluence for team documentation and knowledge management",
    category=ConnectorCategory.DOC_MGMT,
    status=ConnectorStatus.AVAILABLE,
    icon="confluence",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="basic",
    config_fields=[
        {"name": "instance_url", "type": "url", "required": True, "label": "Instance URL"},
        {"name": "space_key", "type": "string", "required": False, "label": "Space Key"},
    ],
    env_vars=["CONFLUENCE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN"],
)

GOOGLE_DRIVE_CONNECTOR = ConnectorDefinition(
    connector_id="google_drive",
    name="Google Drive",
    description="Google Drive for cloud document storage and collaboration",
    category=ConnectorCategory.DOC_MGMT,
    status=ConnectorStatus.AVAILABLE,
    icon="google",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": False, "label": "API Base URL"},
            {"name": "folder_id", "type": "string", "required": False, "label": "Root Folder ID"},
        ]
    ),
    env_vars=[
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
    ],
)

# ERP Category
SAP_CONNECTOR = ConnectorDefinition(
    connector_id="sap",
    name="SAP",
    description="SAP ERP for enterprise resource planning and financials",
    category=ConnectorCategory.ERP,
    status=ConnectorStatus.AVAILABLE,
    icon="sap",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="basic",
    config_fields=[
        {"name": "instance_url", "type": "url", "required": True, "label": "SAP Instance URL"},
        {"name": "client_id", "type": "string", "required": True, "label": "SAP Client ID"},
    ],
    env_vars=["SAP_URL", "SAP_USERNAME", "SAP_PASSWORD", "SAP_CLIENT"],
)

SAP_MCP_CONNECTOR = ConnectorDefinition(
    connector_id="sap_mcp",
    system="sap",
    name="SAP (MCP)",
    description="Sync SAP ERP data via MCP-backed OData services.",
    category=ConnectorCategory.ERP,
    status=ConnectorStatus.BETA,
    icon="sap",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="mcp",
    mcp_server_id="sap",
    config_fields=MCP_CONFIG_FIELDS,
    supported_operations=[
        "list_invoices",
        "list_goods_receipts",
        "list_purchase_orders",
        "list_suppliers",
    ],
    prefer_mcp=True,
)

ORACLE_CONNECTOR = ConnectorDefinition(
    connector_id="oracle",
    name="Oracle ERP Cloud",
    description="Oracle ERP Cloud for enterprise resource planning",
    category=ConnectorCategory.ERP,
    status=ConnectorStatus.AVAILABLE,
    icon="oracle",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": True, "label": "Oracle Cloud URL"},
        ]
    ),
    env_vars=[
        "ORACLE_URL",
        "ORACLE_CLIENT_ID",
        "ORACLE_CLIENT_SECRET",
        "ORACLE_REFRESH_TOKEN",
    ],
)

NETSUITE_CONNECTOR = ConnectorDefinition(
    connector_id="netsuite",
    name="NetSuite",
    description="Oracle NetSuite for ERP and financials",
    category=ConnectorCategory.ERP,
    status=ConnectorStatus.AVAILABLE,
    icon="netsuite",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": False, "label": "REST Base URL"},
            {"name": "account_id", "type": "string", "required": True, "label": "Account ID"},
        ]
    ),
    env_vars=[
        "NETSUITE_ACCOUNT_ID",
        "NETSUITE_CONSUMER_KEY",
        "NETSUITE_CONSUMER_SECRET",
        "NETSUITE_REFRESH_TOKEN",
    ],
)

# HRIS Category
WORKDAY_CONNECTOR = ConnectorDefinition(
    connector_id="workday",
    name="Workday",
    description="Workday HCM for human capital management",
    category=ConnectorCategory.HRIS,
    status=ConnectorStatus.AVAILABLE,
    icon="workday",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": False, "label": "API Base URL"},
            {"name": "tenant_name", "type": "string", "required": True, "label": "Tenant Name"},
        ]
    ),
    env_vars=[
        "WORKDAY_API_URL",
        "WORKDAY_CLIENT_ID",
        "WORKDAY_CLIENT_SECRET",
        "WORKDAY_REFRESH_TOKEN",
    ],
)

WORKDAY_MCP_CONNECTOR = ConnectorDefinition(
    connector_id="workday_mcp",
    system="workday",
    name="Workday (MCP)",
    description="Sync Workday HRIS data via MCP services.",
    category=ConnectorCategory.HRIS,
    status=ConnectorStatus.BETA,
    icon="workday",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="mcp",
    mcp_server_id="workday",
    config_fields=MCP_CONFIG_FIELDS,
    supported_operations=[
        "list_workers",
        "list_job_profiles",
        "list_positions",
        "list_organizations",
    ],
    prefer_mcp=True,
)

SAP_SUCCESSFACTORS_CONNECTOR = ConnectorDefinition(
    connector_id="sap_successfactors",
    name="SAP SuccessFactors",
    description="SAP SuccessFactors for human capital management",
    category=ConnectorCategory.HRIS,
    status=ConnectorStatus.AVAILABLE,
    icon="sap",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "api_server", "type": "url", "required": True, "label": "API Server URL"},
            {"name": "company_id", "type": "string", "required": True, "label": "Company ID"},
        ]
    ),
    env_vars=[
        "SF_API_SERVER",
        "SF_COMPANY_ID",
        "SF_CLIENT_ID",
        "SF_CLIENT_SECRET",
        "SF_REFRESH_TOKEN",
    ],
)

ADP_CONNECTOR = ConnectorDefinition(
    connector_id="adp",
    name="ADP",
    description="ADP Workforce Now for payroll and HR",
    category=ConnectorCategory.HRIS,
    status=ConnectorStatus.AVAILABLE,
    icon="adp",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="oauth2",
    config_fields=_with_rotation_fields([]),
    env_vars=["ADP_API_URL", "ADP_CLIENT_ID", "ADP_CLIENT_SECRET", "ADP_REFRESH_TOKEN"],
)

# Collaboration Category
M365_CONNECTOR = ConnectorDefinition(
    connector_id="m365",
    name="Microsoft 365",
    description="Microsoft 365 suite for Teams, Exchange, SharePoint, Planner, OneDrive, Power BI, and Viva.",
    category=ConnectorCategory.COLLABORATION,
    status=ConnectorStatus.BETA,
    icon="microsoft",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": False, "label": "Graph API Base URL"},
            {"name": "tenant_id", "type": "string", "required": True, "label": "Tenant ID"},
            {
                "name": "client_id",
                "type": "string",
                "required": True,
                "label": "App (client) ID",
            },
            {
                "name": "app_object_id",
                "type": "string",
                "required": False,
                "label": "App Object ID",
            },
            {
                "name": "service_principal_object_id",
                "type": "string",
                "required": False,
                "label": "Service Principal Object ID",
            },
            {
                "name": "application_id_uri",
                "type": "string",
                "required": False,
                "label": "Application ID URI",
            },
            {
                "name": "scopes",
                "type": "multiselect",
                "required": False,
                "label": "Microsoft Graph Scopes",
                "options": [
                    "User.Read",
                    "Group.Read.All",
                    "Team.ReadBasic.All",
                    "Channel.ReadBasic.All",
                    "Mail.Read",
                    "Calendars.Read",
                    "Files.Read.All",
                    "Sites.Read.All",
                    "Tasks.Read",
                    "Reports.Read.All",
                    "EmployeeExperience.Read.All",
                ],
            },
            {
                "name": "enable_teams",
                "type": "boolean",
                "required": False,
                "label": "Enable Teams workload",
            },
            {
                "name": "enable_exchange",
                "type": "boolean",
                "required": False,
                "label": "Enable Exchange/Outlook workload",
            },
            {
                "name": "enable_sharepoint",
                "type": "boolean",
                "required": False,
                "label": "Enable SharePoint workload",
            },
            {
                "name": "enable_planner",
                "type": "boolean",
                "required": False,
                "label": "Enable Planner workload",
            },
            {
                "name": "enable_onedrive",
                "type": "boolean",
                "required": False,
                "label": "Enable OneDrive workload",
            },
            {
                "name": "enable_power_bi",
                "type": "boolean",
                "required": False,
                "label": "Enable Power BI workload",
            },
            {
                "name": "enable_viva",
                "type": "boolean",
                "required": False,
                "label": "Enable Viva workload",
            },
        ]
    ),
    env_vars=[
        "M365_API_URL",
        "M365_TENANT_ID",
        "M365_CLIENT_ID",
        "M365_CLIENT_SECRET",
        "M365_REFRESH_TOKEN",
        "M365_SCOPES",
    ],
)

TEAMS_CONNECTOR = ConnectorDefinition(
    connector_id="teams",
    name="Microsoft Teams",
    description="Microsoft Teams for collaboration and communication",
    category=ConnectorCategory.COLLABORATION,
    status=ConnectorStatus.AVAILABLE,
    icon="teams",
    supported_sync_directions=[SyncDirection.OUTBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": False, "label": "Graph API Base URL"},
            {"name": "team_id", "type": "string", "required": False, "label": "Team ID"},
            {"name": "channel_id", "type": "string", "required": False, "label": "Channel ID"},
        ]
    ),
    env_vars=[
        "TEAMS_CLIENT_ID",
        "TEAMS_CLIENT_SECRET",
        "TEAMS_REFRESH_TOKEN",
        "TEAMS_TENANT_ID",
    ],
)

TEAMS_MCP_CONNECTOR = ConnectorDefinition(
    connector_id="teams_mcp",
    system="teams",
    name="Microsoft Teams (MCP)",
    description="Sync Teams channels and messages via an MCP server.",
    category=ConnectorCategory.COLLABORATION,
    status=ConnectorStatus.BETA,
    icon="teams",
    supported_sync_directions=[SyncDirection.OUTBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="mcp",
    mcp_server_id="teams",
    config_fields=MCP_CONFIG_FIELDS,
    supported_operations=["list", "create"],
    prefer_mcp=True,
)

SLACK_CONNECTOR = ConnectorDefinition(
    connector_id="slack",
    name="Slack",
    description="Slack for team messaging and collaboration",
    category=ConnectorCategory.COLLABORATION,
    status=ConnectorStatus.AVAILABLE,
    icon="slack",
    supported_sync_directions=[SyncDirection.OUTBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": False, "label": "API Base URL"},
            {"name": "workspace_id", "type": "string", "required": False, "label": "Workspace ID"},
            {
                "name": "default_channel",
                "type": "string",
                "required": False,
                "label": "Default Channel",
            },
        ]
    ),
    env_vars=["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"],
)

SLACK_MCP_CONNECTOR = ConnectorDefinition(
    connector_id="slack_mcp",
    system="slack",
    name="Slack (MCP)",
    description="Sync collaboration metadata and notifications from Slack via an MCP server.",
    category=ConnectorCategory.COLLABORATION,
    status=ConnectorStatus.BETA,
    icon="slack",
    supported_sync_directions=[
        SyncDirection.INBOUND,
        SyncDirection.OUTBOUND,
        SyncDirection.BIDIRECTIONAL,
    ],
    auth_type="mcp",
    mcp_server_id="slack",
    config_fields=MCP_CONFIG_FIELDS,
    supported_operations=["list", "create"],
    prefer_mcp=True,
)

ZOOM_CONNECTOR = ConnectorDefinition(
    connector_id="zoom",
    name="Zoom",
    description="Zoom for video conferencing",
    category=ConnectorCategory.COLLABORATION,
    status=ConnectorStatus.AVAILABLE,
    icon="zoom",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.OUTBOUND],
    auth_type="oauth2",
    config_fields=_with_rotation_fields([]),
    env_vars=[
        "ZOOM_CLIENT_ID",
        "ZOOM_CLIENT_SECRET",
        "ZOOM_REFRESH_TOKEN",
    ],
)

# GRC Category
SERVICENOW_GRC_CONNECTOR = ConnectorDefinition(
    connector_id="servicenow_grc",
    name="ServiceNow GRC",
    description="ServiceNow Governance, Risk, and Compliance",
    category=ConnectorCategory.GRC,
    status=ConnectorStatus.AVAILABLE,
    icon="servicenow",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="oauth2",
    config_fields=_with_rotation_fields(
        [
            {"name": "instance_url", "type": "url", "required": True, "label": "Instance URL"},
        ]
    ),
    env_vars=[
        "SERVICENOW_URL",
        "SERVICENOW_CLIENT_ID",
        "SERVICENOW_CLIENT_SECRET",
        "SERVICENOW_REFRESH_TOKEN",
    ],
)

ARCHER_CONNECTOR = ConnectorDefinition(
    connector_id="archer",
    name="RSA Archer",
    description="RSA Archer for integrated risk management",
    category=ConnectorCategory.GRC,
    status=ConnectorStatus.AVAILABLE,
    icon="archer",
    supported_sync_directions=[SyncDirection.INBOUND],
    auth_type="api_key",
    config_fields=[
        {"name": "instance_url", "type": "url", "required": True, "label": "Instance URL"},
    ],
    env_vars=["ARCHER_URL", "ARCHER_API_KEY"],
)

LOGICGATE_CONNECTOR = ConnectorDefinition(
    connector_id="logicgate",
    name="LogicGate",
    description="LogicGate for risk and compliance management",
    category=ConnectorCategory.GRC,
    status=ConnectorStatus.AVAILABLE,
    icon="logicgate",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL],
    auth_type="api_key",
    config_fields=[
        {"name": "instance_url", "type": "url", "required": False, "label": "API Base URL"},
        {"name": "subdomain", "type": "string", "required": True, "label": "Subdomain"},
    ],
    env_vars=["LOGICGATE_API_URL", "LOGICGATE_API_KEY"],
)

REGULATORY_COMPLIANCE_CONNECTOR = ConnectorDefinition(
    connector_id="regulatory_compliance",
    name="Regulatory Compliance",
    description="Regulatory compliance APIs for HIPAA and FDA CFR 21 Part 11 audit trails",
    category=ConnectorCategory.COMPLIANCE,
    status=ConnectorStatus.BETA,
    icon="shield-check",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.OUTBOUND],
    auth_type="api_key",
    config_fields=[
        {
            "name": "endpoint_url",
            "type": "url",
            "required": True,
            "label": "Compliance API Endpoint",
        },
        {
            "name": "api_key",
            "type": "string",
            "required": True,
            "label": "API Key",
        },
        {
            "name": "supported_regulations",
            "type": "string",
            "required": False,
            "label": "Supported Regulations (comma-separated)",
        },
    ],
    env_vars=["REGULATORY_COMPLIANCE_ENDPOINT", "REGULATORY_COMPLIANCE_API_KEY"],
)

# IoT Integrations Category
IOT_CONNECTOR = ConnectorDefinition(
    connector_id="iot",
    name="IoT Integrations",
    description="Custom hardware and sensor integrations via device endpoints",
    category=ConnectorCategory.IOT,
    status=ConnectorStatus.AVAILABLE,
    icon="cpu-chip",
    supported_sync_directions=[SyncDirection.INBOUND, SyncDirection.OUTBOUND],
    auth_type="api_key",
    config_fields=[
        {
            "name": "protocol",
            "type": "string",
            "required": False,
            "label": "Protocol (http, https, mqtt)",
        },
        {
            "name": "device_endpoint",
            "type": "url",
            "required": False,
            "label": "Device Endpoint",
        },
        {
            "name": "auth_token",
            "type": "string",
            "required": False,
            "label": "Authentication Token",
        },
        {
            "name": "device_ids",
            "type": "string",
            "required": False,
            "label": "Device IDs (comma-separated)",
        },
        {
            "name": "sensor_types",
            "type": "string",
            "required": False,
            "label": "Supported Sensor Types (comma-separated)",
        },
        {
            "name": "mqtt_broker",
            "type": "string",
            "required": False,
            "label": "MQTT Broker Host",
        },
        {
            "name": "mqtt_port",
            "type": "number",
            "required": False,
            "label": "MQTT Broker Port",
        },
        {
            "name": "mqtt_username",
            "type": "string",
            "required": False,
            "label": "MQTT Username",
        },
        {
            "name": "mqtt_password",
            "type": "string",
            "required": False,
            "label": "MQTT Password",
        },
        {
            "name": "mqtt_topic",
            "type": "string",
            "required": False,
            "label": "MQTT Topic",
        },
        {
            "name": "poll_interval_seconds",
            "type": "number",
            "required": False,
            "label": "Polling Interval (seconds)",
        },
    ],
    env_vars=[
        "IOT_PROTOCOL",
        "IOT_DEVICE_ENDPOINT",
        "IOT_AUTH_TOKEN",
        "IOT_DEVICE_IDS",
        "IOT_SENSOR_TYPES",
        "IOT_MQTT_BROKER",
        "IOT_MQTT_PORT",
        "IOT_MQTT_USERNAME",
        "IOT_MQTT_PASSWORD",
        "IOT_MQTT_TOPIC",
        "IOT_POLL_INTERVAL_SECONDS",
    ],
)


# =============================================================================
# REGISTRY
# =============================================================================

ALL_CONNECTORS: list[ConnectorDefinition] = [
    # PPM
    PLANVIEW_CONNECTOR,
    PLANVIEW_MCP_CONNECTOR,
    CLARITY_CONNECTOR,
    CLARITY_MCP_CONNECTOR,
    MS_PROJECT_SERVER_CONNECTOR,
    # PM
    JIRA_CONNECTOR,
    JIRA_MCP_CONNECTOR,
    AZURE_DEVOPS_CONNECTOR,
    MONDAY_CONNECTOR,
    ASANA_CONNECTOR,
    ASANA_MCP_CONNECTOR,
    # Doc Management
    SHAREPOINT_CONNECTOR,
    CONFLUENCE_CONNECTOR,
    GOOGLE_DRIVE_CONNECTOR,
    # ERP
    SAP_CONNECTOR,
    SAP_MCP_CONNECTOR,
    ORACLE_CONNECTOR,
    NETSUITE_CONNECTOR,
    # HRIS
    WORKDAY_CONNECTOR,
    WORKDAY_MCP_CONNECTOR,
    SAP_SUCCESSFACTORS_CONNECTOR,
    ADP_CONNECTOR,
    # Collaboration
    M365_CONNECTOR,
    TEAMS_CONNECTOR,
    TEAMS_MCP_CONNECTOR,
    SLACK_CONNECTOR,
    SLACK_MCP_CONNECTOR,
    ZOOM_CONNECTOR,
    # GRC
    SERVICENOW_GRC_CONNECTOR,
    ARCHER_CONNECTOR,
    LOGICGATE_CONNECTOR,
    # Compliance
    REGULATORY_COMPLIANCE_CONNECTOR,
    # IoT
    IOT_CONNECTOR,
]

CONNECTORS_BY_ID: dict[str, ConnectorDefinition] = {c.connector_id: c for c in ALL_CONNECTORS}

CONNECTORS_BY_CATEGORY: dict[ConnectorCategory, list[ConnectorDefinition]] = {}
for connector in ALL_CONNECTORS:
    if connector.category not in CONNECTORS_BY_CATEGORY:
        CONNECTORS_BY_CATEGORY[connector.category] = []
    CONNECTORS_BY_CATEGORY[connector.category].append(connector)


DEMO_CONNECTOR_CONFIG_ROOT = Path(__file__).resolve().parents[4] / "config" / "connectors" / "mock"


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
