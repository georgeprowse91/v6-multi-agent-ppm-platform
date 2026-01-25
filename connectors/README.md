# Connectors

Integration connectors for external systems (PPM tools, finance, collaboration).
Each connector has source code, mapping templates, and tests.

## Quickstart

Run a connector in dry-run mode to validate its manifest and mappings:

```bash
python -m tools.connector_runner run-connector --name jira --dry-run
```

## How to verify

```bash
ls connectors/jira
```

Expected output includes `manifest.yaml`, `mappings/`, and `src/`.

## Key files

- `connectors/<name>/manifest.yaml`: connector identity and versioning.
- `connectors/<name>/mappings/`: field mapping templates.
- `connectors/<name>/src/`: connector implementation.
- `connectors/sdk/`: shared SDK utilities.

## Example

Inspect the Jira connector manifest ID:

```bash
rg -n "id:" connectors/jira/manifest.yaml
```

## Next steps

- Implement connector-specific sync logic under each `connectors/<name>/src/`.
- Wire connector runs into `services/data-sync-service/` workflows.
