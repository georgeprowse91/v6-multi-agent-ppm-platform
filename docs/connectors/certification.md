# Connector Certification

## Purpose

Define the certification workflow required before a connector can be enabled in production environments.

## Architecture-level context

Certification ensures connectors enforce the same security, data quality, and operational standards as the core platform. Evidence is attached to the connector registry and referenced by the orchestration layer before a connector can be activated.

## Certification checklist

| Step | Evidence | Artifact path |
| --- | --- | --- |
| Schema coverage | Mapping files cover required fields | `connectors/<name>/mappings/*.yaml` |
| Auth validation | Token flow tested and rotated | `config/<env>/connector-auth.yaml` |
| Sandbox tests | CRUD against vendor sandbox | `connectors/<name>/tests/` |
| Rate-limit handling | Retry policy documented | `connectors/<name>/manifest.yaml` |
| Security review | Secrets stored in vault | `docs/architecture/security-architecture.md` |
| Data lineage | Lineage artifact emitted | `data/lineage/` |

## Usage example

Record certification status in the registry:

```bash
rg -n "certification" connectors/registry/connectors.json
```

## How to verify

Ensure a connector has at least one mapping file:

```bash
ls connectors/jira/mappings
```

Expected output: mapping files such as `project.yaml`.

## Implementation status

- **Planned**: automated certification evidence collection.
- **Partially implemented**: manual checklist and registry metadata.

## Related docs

- [Connector Overview](overview.md)
- [Connector Registry](../../connectors/registry/connectors.json)
- [Data Lineage](../data/lineage.md)
