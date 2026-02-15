# Slack Field Mappings

## Purpose

Define how Slack payloads map into the platform's canonical schemas under `data/schemas/`.

## What's inside

- [integrations/connectors/slack/mappings/project.yaml](/integrations/connectors/slack/mappings/project.yaml): Project mapping definition for connector data.

## How it's used

Referenced by `integrations/connectors/slack/manifest.yaml` and loaded by `tools.connector_runner` when synchronizing data.

## How to run / develop / test

Validate mappings via a dry-run connector execution:

```bash
python -m tools.connector_runner run-connector --name slack --dry-run
```

## Configuration

No direct configuration. Connector authentication and sync options live in `integrations/connectors/slack/manifest.yaml` and environment variables referenced by `src/`.

## Troubleshooting

- Dry-run fails on missing mappings: ensure the files listed in the manifest exist.
- Schema mismatch errors: compare mapping targets with `data/schemas/`.
