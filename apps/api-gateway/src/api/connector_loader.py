from __future__ import annotations

import importlib

_CONNECTOR_CLASS_MAP: dict[str, tuple[str, str]] = {
    "jira": ("jira_connector", "JiraConnector"),
    "planview": ("planview_connector", "PlanviewConnector"),
    "clarity": ("clarity_connector", "ClarityConnector"),
    "ms_project_server": ("ms_project_server_connector", "MsProjectServerConnector"),
    "azure_devops": ("azure_devops_connector", "AzureDevOpsConnector"),
    "monday": ("monday_connector", "MondayConnector"),
    "asana": ("asana_connector", "AsanaConnector"),
    "sharepoint": ("sharepoint_connector", "SharePointConnector"),
    "confluence": ("confluence_connector", "ConfluenceConnector"),
    "google_drive": ("google_drive_connector", "GoogleDriveConnector"),
    "sap": ("sap_connector", "SapConnector"),
    "oracle": ("oracle_connector", "OracleConnector"),
    "netsuite": ("netsuite_connector", "NetSuiteConnector"),
    "workday": ("workday_connector", "WorkdayConnector"),
    "sap_successfactors": ("sap_successfactors_connector", "SapSuccessFactorsConnector"),
    "adp": ("adp_connector", "AdpConnector"),
    "teams": ("teams_connector", "TeamsConnector"),
    "slack": ("slack_connector", "SlackConnector"),
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


def get_connector_class(connector_id: str):
    module_info = _CONNECTOR_CLASS_MAP.get(connector_id)
    if not module_info:
        return None
    module_name, class_name = module_info
    module = importlib.import_module(module_name)
    return getattr(module, class_name, None)
