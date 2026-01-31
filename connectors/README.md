# Connectors

## Purpose

Provide the integration layer for synchronizing external systems with the platform's canonical data model.

## What's inside

Registered and packaged connectors include:

- `connectors/jira`: Jira Cloud sync + webhook scaffolding (inbound projects/work items).
- `connectors/planview`: Planview portfolio integration (inbound projects, outbound dry-run mapping).
  - Configuration: `PLANVIEW_INSTANCE_URL`, `PLANVIEW_CLIENT_ID`, `PLANVIEW_CLIENT_SECRET`, `PLANVIEW_REFRESH_TOKEN`.
- `connectors/clarity`: Clarity PPM integration (inbound projects, outbound dry-run mapping).
  - Configuration: `CLARITY_INSTANCE_URL`, `CLARITY_CLIENT_ID`, `CLARITY_CLIENT_SECRET`, `CLARITY_REFRESH_TOKEN`.
- `connectors/azure_devops`: Azure DevOps work item sync (inbound and outbound).
- `connectors/servicenow`: ServiceNow project sync (inbound projects, outbound dry-run mapping).
  - Configuration: `SERVICENOW_URL`, `SERVICENOW_CLIENT_ID`, `SERVICENOW_CLIENT_SECRET`, `SERVICENOW_REFRESH_TOKEN`, `SERVICENOW_TOKEN_URL`.
- `connectors/sap`: SAP finance and portfolio sync (inbound projects, outbound dry-run mapping).
  - Configuration: `SAP_URL`, `SAP_USERNAME`, `SAP_PASSWORD`, optional `SAP_CLIENT`.
- `connectors/workday`: Workday HR and cost center sync (inbound projects, outbound dry-run mapping).
  - Configuration: `WORKDAY_API_URL`, `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`.
- `connectors/salesforce`: Salesforce demand and CRM sync (inbound projects, outbound dry-run mapping).
  - Configuration: `SALESFORCE_INSTANCE_URL`, `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_REFRESH_TOKEN`.
- `connectors/sharepoint`: SharePoint document sync (inbound and outbound).
- `connectors/slack`: Slack notifications and commands (inbound channels, outbound messages).
  - Configuration: `SLACK_API_URL`, `SLACK_BOT_TOKEN`.
- `connectors/teams`: Microsoft Teams notifications and cards (inbound teams, outbound messages).
  - Configuration: `TEAMS_API_URL`, `TEAMS_CLIENT_ID`, `TEAMS_CLIENT_SECRET`, `TEAMS_REFRESH_TOKEN`.

Additional connector folders exist for future expansion (e.g., Asana, Monday.com, Oracle, NetSuite) and can be promoted by adding manifests, mappings, and registry entries.

Connector metadata is stored in `connectors/registry/connectors.json` and each connector includes a `manifest.yaml` plus mapping definitions under `mappings/`.

## How it's used

Connectors are discovered by `tools.connector_runner` and referenced by the registry metadata in `connectors/registry/`. Each connector includes a manifest and mapping files.

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
