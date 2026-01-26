# Connectors

## Purpose

Provide the integration layer for synchronizing external systems with the platform's canonical data model.

## What's inside

- `connectors/azure_devops`: Subdirectory containing azure devops assets for this area.
- `connectors/jira`: Subdirectory containing jira assets for this area.
- `connectors/planview`: Subdirectory containing planview assets for this area.
- `connectors/registry`: Registry assets and indexes.
- `connectors/salesforce`: Subdirectory containing salesforce assets for this area.
- `connectors/sap`: Subdirectory containing sap assets for this area.

## How it's used

Connectors are discovered by `tools.connector_runner` and referenced by the registry metadata in `connectors/registry/`. Each connector includes a manifest and mapping files.

## How to run / develop / test

List available connectors and validate a dry-run execution:

```bash
python -m tools.connector_runner list-connectors
python -m tools.connector_runner run-connector --name jira --dry-run
```

## Configuration

Connector credentials are supplied via `.env` (see `.env.example`) or secret managers, and connector-specific settings are stored in each `manifest.yaml`.

## Troubleshooting

- Connector not listed: ensure `manifest.yaml` exists in the connector folder.
- Authentication errors: verify connector-specific environment variables.
