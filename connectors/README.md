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

- [`connectors/jira`](./jira/): Jira Cloud sync + webhook scaffolding (inbound projects/work items).
- [`connectors/planview`](./planview/): Planview portfolio integration (inbound projects, outbound dry-run mapping).
  - Configuration: `PLANVIEW_INSTANCE_URL`, `PLANVIEW_CLIENT_ID`, `PLANVIEW_CLIENT_SECRET`, `PLANVIEW_REFRESH_TOKEN`.
- [`connectors/clarity`](./clarity/): Clarity PPM integration (inbound projects, outbound dry-run mapping).
  - Configuration: `CLARITY_INSTANCE_URL`, `CLARITY_CLIENT_ID`, `CLARITY_CLIENT_SECRET`, `CLARITY_REFRESH_TOKEN`.
- [`connectors/azure_devops`](./azure_devops/): Azure DevOps work item sync (inbound and outbound).
- [`connectors/servicenow`](./servicenow/): ServiceNow project sync (inbound projects, outbound dry-run mapping).
  - Configuration: `SERVICENOW_URL`, `SERVICENOW_CLIENT_ID`, `SERVICENOW_CLIENT_SECRET`, `SERVICENOW_REFRESH_TOKEN`, `SERVICENOW_TOKEN_URL`.
- [`connectors/sap`](./sap/): SAP finance and portfolio sync (inbound projects, outbound dry-run mapping).
  - Configuration: `SAP_URL`, `SAP_USERNAME`, `SAP_PASSWORD`, optional `SAP_CLIENT`.
- [`connectors/workday`](./workday/): Workday HR and cost center sync (inbound projects, outbound dry-run mapping).
  - Configuration: `WORKDAY_API_URL`, `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`.
- [`connectors/salesforce`](./salesforce/): Salesforce demand and CRM sync (inbound projects, outbound dry-run mapping).
  - Configuration: `SALESFORCE_INSTANCE_URL`, `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_REFRESH_TOKEN`.
- [`connectors/sharepoint`](./sharepoint/): SharePoint document sync (inbound and outbound).
- [`connectors/slack`](./slack/): Slack notifications and commands (inbound channels, outbound messages).
  - Configuration: `SLACK_API_URL`, `SLACK_BOT_TOKEN`.
- [`connectors/teams`](./teams/): Microsoft Teams notifications and cards (inbound teams, outbound messages).
  - Configuration: `TEAMS_API_URL`, `TEAMS_CLIENT_ID`, `TEAMS_CLIENT_SECRET`, `TEAMS_REFRESH_TOKEN`.
- [`connectors/smartsheet`](./smartsheet/): Smartsheet schedule and sheet sync (inbound sheets, outbound updates).
  - Configuration: `SMARTSHEET_API_URL`, `SMARTSHEET_API_TOKEN`.
- [`connectors/outlook`](./outlook/): Outlook calendar sync via Microsoft Graph (inbound events, outbound invites).
  - Configuration: `OUTLOOK_API_URL`, `OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET`, `OUTLOOK_REFRESH_TOKEN`.
- [`connectors/google_calendar`](./google_calendar/): Google Calendar event sync (inbound events, outbound invites).
  - Configuration: `GOOGLE_CALENDAR_BASE_URL`, `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_REFRESH_TOKEN`.
- [`connectors/azure_communication_services`](./azure_communication_services/): Azure Communication Services messaging (outbound SMS/email).
  - Configuration: `AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING`, `ACS_ENDPOINT`, `ACS_ACCESS_KEY`.
- [`connectors/twilio`](./twilio/): Twilio SMS messaging (outbound SMS, inbound message logs).
  - Configuration: `TWILIO_API_URL`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`.
- [`connectors/notification_hubs`](./notification_hubs/): Azure Notification Hubs push notifications.
  - Configuration: `AZURE_NOTIFICATION_HUBS_NAMESPACE`, `AZURE_NOTIFICATION_HUBS_NAME`, `AZURE_NOTIFICATION_HUBS_SAS_KEY_NAME`, `AZURE_NOTIFICATION_HUBS_SAS_KEY`.

Additional connector folders for future expansion:

- [`connectors/adp`](./adp/): ADP HR integration.
- [`connectors/archer`](./archer/): RSA Archer GRC integration.
- [`connectors/asana`](./asana/): Asana project management.
- [`connectors/confluence`](./confluence/): Confluence document integration.
- [`connectors/google_drive`](./google_drive/): Google Drive document integration.
- [`connectors/iot`](./iot/): IoT sensor data integration.
- [`connectors/logicgate`](./logicgate/): LogicGate GRC integration.
- [`connectors/monday`](./monday/): Monday.com project management.
- [`connectors/ms_project_server`](./ms_project_server/): Microsoft Project Server integration.
- [`connectors/netsuite`](./netsuite/): NetSuite ERP integration.
- [`connectors/oracle`](./oracle/): Oracle ERP integration.
- [`connectors/sap_successfactors`](./sap_successfactors/): SAP SuccessFactors HR integration.
- [`connectors/zoom`](./zoom/): Zoom video conferencing integration.

These can be promoted by adding manifests, mappings, and registry entries.

Connector metadata is stored in [`connectors/registry/connectors.json`](./registry/) and each connector includes a `manifest.yaml` plus mapping definitions under `mappings/`.

Shared utilities:

- [`connectors/sdk`](./sdk/): Shared helpers and scaffolding for building connectors.
- [`connectors/integration`](./integration/): Integration framework with base connector classes and connector registry.

## How it's used

Connectors are discovered by `tools.connector_runner` and referenced by the registry metadata in [`connectors/registry/`](./registry/). Each connector includes a manifest and mapping files.

## How to run / develop / test

List available connectors and validate a dry-run execution:

```bash
python -m tools.connector_runner list-connectors
python -m tools.connector_runner run-connector --name jira --dry-run
```

## Configuration

Connector credentials are supplied via `.env` (see `.env.example`) or secret managers, and connector-specific settings are stored in each `manifest.yaml` and in `config/connectors/integrations.yaml`.

## Troubleshooting

- Connector not listed: ensure `manifest.yaml` exists in the connector folder.
- Authentication errors: verify connector-specific environment variables.
