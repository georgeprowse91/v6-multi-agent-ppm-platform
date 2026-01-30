# Connectors

## Purpose

Provide the integration layer for synchronizing external systems with the platform's canonical data model.

## What's inside

Registered and packaged connectors include:

- `connectors/jira`: Jira Cloud sync + webhook scaffolding.
- `connectors/planview`: Planview portfolio integration.
- `connectors/clarity`: Clarity PPM integration.
- `connectors/azure_devops`: Azure DevOps work item sync.
- `connectors/servicenow`: ServiceNow project and change data sync.
- `connectors/sap`: SAP finance and portfolio sync.
- `connectors/workday`: Workday HR and cost center sync.
- `connectors/salesforce`: Salesforce demand and CRM sync.
- `connectors/sharepoint`: SharePoint document sync.
- `connectors/slack`: Slack notifications and commands.
- `connectors/teams`: Microsoft Teams notifications and cards.

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
