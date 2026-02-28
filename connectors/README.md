# Connectors

## Purpose

Provide the integration layer for synchronizing external systems with the platform's canonical data model.

## Directory structure

| Folder | Description |
| --- | --- |
| [adp/](./adp/) | ADP HR integration connector |
| [archer/](./archer/) | RSA Archer GRC connector |
| [asana/](./asana/) | Asana project management connector |
| [azure_communication_services/](./azure_communication_services/) | Azure Communication Services messaging connector |
| [azure_devops/](./azure_devops/) | Azure DevOps work item sync connector |
| [clarity/](./clarity/) | Clarity PPM integration connector |
| [confluence/](./confluence/) | Confluence document connector |
| [google_calendar/](./google_calendar/) | Google Calendar event sync connector |
| [google_drive/](./google_drive/) | Google Drive document connector |
| [integration/](./integration/) | Shared connector integration framework and utilities |
| [iot/](./iot/) | IoT sensor data connector |
| [jira/](./jira/) | Jira Cloud sync connector |
| [logicgate/](./logicgate/) | LogicGate GRC connector |
| [monday/](./monday/) | Monday.com project connector |
| [ms_project_server/](./ms_project_server/) | Microsoft Project Server connector |
| [netsuite/](./netsuite/) | NetSuite ERP connector |
| [notification_hubs/](./notification_hubs/) | Azure Notification Hubs push connector |
| [oracle/](./oracle/) | Oracle ERP connector |
| [outlook/](./outlook/) | Outlook calendar sync connector |
| [planview/](./planview/) | Planview portfolio connector |
| [registry/](./registry/) | Connector registry metadata and schemas |
| [salesforce/](./salesforce/) | Salesforce CRM sync connector |
| [sap/](./sap/) | SAP finance and portfolio connector |
| [sap_successfactors/](./sap_successfactors/) | SAP SuccessFactors HR connector |
| [sdk/](./sdk/) | Connector SDK with shared helpers and scaffolding |
| [servicenow/](./servicenow/) | ServiceNow project sync connector |
| [sharepoint/](./sharepoint/) | SharePoint document sync connector |
| [slack/](./slack/) | Slack notifications connector |
| [smartsheet/](./smartsheet/) | Smartsheet schedule sync connector |
| [teams/](./teams/) | Teams notifications connector |
| [twilio/](./twilio/) | Twilio SMS connector |
| [workday/](./workday/) | Workday HR sync connector |
| [zoom/](./zoom/) | Zoom video conferencing connector |

## What's inside

Registered and packaged connectors include:

- [`integrations/connectors/jira`](./jira/): Jira Cloud sync + webhook scaffolding (inbound projects/work items).
- [`integrations/connectors/planview`](./planview/): Planview portfolio integration (inbound projects, outbound dry-run mapping).
  - Configuration: `PLANVIEW_INSTANCE_URL`, `PLANVIEW_CLIENT_ID`, `PLANVIEW_CLIENT_SECRET`, `PLANVIEW_REFRESH_TOKEN`.
- [`integrations/connectors/clarity`](./clarity/): Clarity PPM integration (inbound projects, outbound dry-run mapping).
  - Configuration: `CLARITY_INSTANCE_URL`, `CLARITY_CLIENT_ID`, `CLARITY_CLIENT_SECRET`, `CLARITY_REFRESH_TOKEN`.
- [`integrations/connectors/azure_devops`](./azure_devops/): Azure DevOps work item sync (inbound and outbound).
- [`integrations/connectors/servicenow`](./servicenow/): ServiceNow project sync (inbound projects, outbound dry-run mapping).
  - Configuration: `SERVICENOW_URL`, `SERVICENOW_CLIENT_ID`, `SERVICENOW_CLIENT_SECRET`, `SERVICENOW_REFRESH_TOKEN`, `SERVICENOW_TOKEN_URL`.
- [`integrations/connectors/sap`](./sap/): SAP finance and portfolio sync (inbound projects, outbound dry-run mapping).
  - Configuration: `SAP_URL`, `SAP_USERNAME`, `SAP_PASSWORD`, optional `SAP_CLIENT`.
- [`integrations/connectors/workday`](./workday/): Workday HR and cost center sync (inbound projects, outbound dry-run mapping).
  - Configuration: `WORKDAY_API_URL`, `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`.
- [`integrations/connectors/salesforce`](./salesforce/): Salesforce demand and CRM sync (inbound projects, outbound dry-run mapping).
  - Configuration: `SALESFORCE_INSTANCE_URL`, `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_REFRESH_TOKEN`.
- [`integrations/connectors/sharepoint`](./sharepoint/): SharePoint document sync (inbound and outbound).
- [`integrations/connectors/slack`](./slack/): Slack notifications and commands (inbound channels, outbound messages).
  - Configuration: `SLACK_API_URL`, `SLACK_BOT_TOKEN`.
- [`integrations/connectors/teams`](./teams/): Microsoft Teams notifications and cards (inbound teams, outbound messages).
  - Configuration: `TEAMS_API_URL`, `TEAMS_CLIENT_ID`, `TEAMS_CLIENT_SECRET`, `TEAMS_REFRESH_TOKEN`.
- [`integrations/connectors/smartsheet`](./smartsheet/): Smartsheet schedule and sheet sync (inbound sheets, outbound updates).
  - Configuration: `SMARTSHEET_API_URL`, `SMARTSHEET_API_TOKEN`.
- [`integrations/connectors/outlook`](./outlook/): Outlook calendar sync via Microsoft Graph (inbound events, outbound invites).
  - Configuration: `OUTLOOK_API_URL`, `OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET`, `OUTLOOK_REFRESH_TOKEN`.
- [`integrations/connectors/google_calendar`](./google_calendar/): Google Calendar event sync (inbound events, outbound invites).
  - Configuration: `GOOGLE_CALENDAR_BASE_URL`, `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_REFRESH_TOKEN`.
- [`integrations/connectors/azure_communication_services`](./azure_communication_services/): Azure Communication Services messaging (outbound SMS/email).
  - Configuration: `AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING`, `ACS_ENDPOINT`, `ACS_ACCESS_KEY`.
- [`integrations/connectors/twilio`](./twilio/): Twilio SMS messaging (outbound SMS, inbound message logs).
  - Configuration: `TWILIO_API_URL`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`.
- [`integrations/connectors/notification_hubs`](./notification_hubs/): Azure Notification Hubs push notifications.
  - Configuration: `AZURE_NOTIFICATION_HUBS_NAMESPACE`, `AZURE_NOTIFICATION_HUBS_NAME`, `AZURE_NOTIFICATION_HUBS_SAS_KEY_NAME`, `AZURE_NOTIFICATION_HUBS_SAS_KEY`.

Additional connector folders for future expansion:

- [`integrations/connectors/adp`](./adp/): ADP HR integration.
- [`integrations/connectors/archer`](./archer/): RSA Archer GRC integration.
- [`integrations/connectors/asana`](./asana/): Asana project management.
- [`integrations/connectors/confluence`](./confluence/): Confluence document integration.
- [`integrations/connectors/google_drive`](./google_drive/): Google Drive document integration.
- [`integrations/connectors/iot`](./iot/): IoT sensor data integration.
- [`integrations/connectors/logicgate`](./logicgate/): LogicGate GRC integration.
- [`integrations/connectors/monday`](./monday/): Monday.com project management.
- [`integrations/connectors/ms_project_server`](./ms_project_server/): Microsoft Project Server integration.
- [`integrations/connectors/netsuite`](./netsuite/): NetSuite ERP integration.
- [`integrations/connectors/oracle`](./oracle/): Oracle ERP integration.
- [`integrations/connectors/sap_successfactors`](./sap_successfactors/): SAP SuccessFactors HR integration.
- [`integrations/connectors/zoom`](./zoom/): Zoom video conferencing integration.

These can be promoted by adding manifests, mappings, and registry entries.

Connector metadata is stored in [`integrations/connectors/registry/connectors.json`](./registry/) and each connector includes a `manifest.yaml` plus mapping definitions under `mappings/`.

Shared utilities:

- [`integrations/connectors/sdk`](./sdk/): Shared helpers and scaffolding for building connectors.
- [`integrations/connectors/integration`](./integration/): Integration framework with base connector classes and connector registry.

## How it's used

Connectors are discovered by `tools.connector_runner` and referenced by the registry metadata in [`integrations/connectors/registry/`](./registry/). Each connector includes a manifest and mapping files.

## How to run / develop / test

List available connectors and validate a dry-run execution:

```bash
python -m tools.connector_runner list-connectors
python -m tools.connector_runner run-connector --name jira --dry-run
```

## Configuration

Connector credentials are supplied via `.env` (see `.env.example`) or secret managers, and connector-specific settings are stored in each `manifest.yaml` and in `config/connectors/integrations.yaml`.
See [REST Connector Configuration](../docs/connectors/rest-connector-config.md) for the project-level configuration matrix and required fields.

## MCP connectors

MCP-enabled connectors support routing through an MCP server for tool execution. For each connector ID, set the MCP server URL and ID in `.env` and optionally supply MCP OAuth credentials when the MCP server requires them. Use `<CONNECTOR>_PREFER_MCP=true` to opt in.

| Connector ID | Required MCP env vars | Optional MCP OAuth env vars |
| --- | --- | --- |
| `planview` | `PLANVIEW_MCP_SERVER_URL`, `PLANVIEW_MCP_SERVER_ID` | `PLANVIEW_MCP_CLIENT_ID`, `PLANVIEW_MCP_CLIENT_SECRET` |
| `clarity` | `CLARITY_MCP_SERVER_URL`, `CLARITY_MCP_SERVER_ID` | `CLARITY_MCP_CLIENT_ID`, `CLARITY_MCP_CLIENT_SECRET` |
| `jira` | `JIRA_MCP_SERVER_URL`, `JIRA_MCP_SERVER_ID` | `JIRA_MCP_CLIENT_ID`, `JIRA_MCP_CLIENT_SECRET` |
| `azure_devops` | `AZURE_DEVOPS_MCP_SERVER_URL`, `AZURE_DEVOPS_MCP_SERVER_ID` | `AZURE_DEVOPS_MCP_CLIENT_ID`, `AZURE_DEVOPS_MCP_CLIENT_SECRET` |
| `sap` | `SAP_MCP_SERVER_URL`, `SAP_MCP_SERVER_ID` | `SAP_MCP_CLIENT_ID`, `SAP_MCP_CLIENT_SECRET` |
| `workday` | `WORKDAY_MCP_SERVER_URL`, `WORKDAY_MCP_SERVER_ID` | `WORKDAY_MCP_CLIENT_ID`, `WORKDAY_MCP_CLIENT_SECRET` |
| `slack` | `SLACK_MCP_SERVER_URL`, `SLACK_MCP_SERVER_ID` | `SLACK_MCP_CLIENT_ID`, `SLACK_MCP_CLIENT_SECRET` |
| `teams` | `TEAMS_MCP_SERVER_URL`, `TEAMS_MCP_SERVER_ID` | `TEAMS_MCP_CLIENT_ID`, `TEAMS_MCP_CLIENT_SECRET` |
| `outlook` | `OUTLOOK_MCP_SERVER_URL`, `OUTLOOK_MCP_SERVER_ID` | `OUTLOOK_MCP_CLIENT_ID`, `OUTLOOK_MCP_CLIENT_SECRET` |
| `google_calendar` | `GOOGLE_CALENDAR_MCP_SERVER_URL`, `GOOGLE_CALENDAR_MCP_SERVER_ID` | `GOOGLE_CALENDAR_MCP_CLIENT_ID`, `GOOGLE_CALENDAR_MCP_CLIENT_SECRET` |
| `smartsheet` | `SMARTSHEET_MCP_SERVER_URL`, `SMARTSHEET_MCP_SERVER_ID` | `SMARTSHEET_MCP_CLIENT_ID`, `SMARTSHEET_MCP_CLIENT_SECRET` |
| `sharepoint` | `SHAREPOINT_MCP_SERVER_URL`, `SHAREPOINT_MCP_SERVER_ID` | `SHAREPOINT_MCP_CLIENT_ID`, `SHAREPOINT_MCP_CLIENT_SECRET` |
| `salesforce` | `SALESFORCE_MCP_SERVER_URL`, `SALESFORCE_MCP_SERVER_ID` | `SALESFORCE_MCP_CLIENT_ID`, `SALESFORCE_MCP_CLIENT_SECRET` |
| `asana` | `ASANA_MCP_SERVER_URL`, `ASANA_MCP_SERVER_ID` | `ASANA_MCP_CLIENT_ID`, `ASANA_MCP_CLIENT_SECRET` |
| `azure_communication_services` | `AZURE_COMMUNICATION_SERVICES_MCP_SERVER_URL`, `AZURE_COMMUNICATION_SERVICES_MCP_SERVER_ID` | `AZURE_COMMUNICATION_SERVICES_MCP_CLIENT_ID`, `AZURE_COMMUNICATION_SERVICES_MCP_CLIENT_SECRET` |
| `twilio` | `TWILIO_MCP_SERVER_URL`, `TWILIO_MCP_SERVER_ID` | `TWILIO_MCP_CLIENT_ID`, `TWILIO_MCP_CLIENT_SECRET` |
| `notification_hubs` | `AZURE_NOTIFICATION_HUBS_MCP_SERVER_URL`, `AZURE_NOTIFICATION_HUBS_MCP_SERVER_ID` | `AZURE_NOTIFICATION_HUBS_MCP_CLIENT_ID`, `AZURE_NOTIFICATION_HUBS_MCP_CLIENT_SECRET` |

## Troubleshooting

- Connector not listed: ensure `manifest.yaml` exists in the connector folder.
- Authentication errors: verify connector-specific environment variables.
