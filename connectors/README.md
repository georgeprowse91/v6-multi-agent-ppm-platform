# Connectors

## Purpose

Provide the integration layer that synchronizes external systems (PPM, ERP, HR, collaboration) with the platform’s canonical data model.

## Architecture-level context

Connectors translate external payloads into the canonical schemas stored in `data/schemas/`, emit lineage events to `data/lineage/`, and enforce authentication and rate-limit policies described in `docs/connectors/overview.md`.

## Quickstart

Run a connector in dry-run mode to validate its manifest and mappings:

```bash
python -m tools.connector_runner run-connector --name jira --dry-run
```

## How to verify

List the Jira connector assets:

```bash
ls connectors/jira
```

Expected output includes `manifest.yaml`, `mappings/`, and `src/`.

## Key files

- `connectors/<name>/manifest.yaml`: connector identity, auth, and sync policies.
- `connectors/<name>/mappings/`: canonical field mappings.
- `connectors/<name>/src/`: connector implementation.
- `connectors/registry/connectors.json`: registry of available connectors.

## Usage example

Inspect the Jira project mapping:

```bash
sed -n '1,160p' connectors/jira/mappings/project.yaml
```

## Related docs

- [Connector Overview](../docs/connectors/overview.md)
- [Connector Certification](../docs/connectors/certification.md)
- [Data Schemas](../data/schemas/)
