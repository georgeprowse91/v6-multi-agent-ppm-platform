# Connector Certification

## Purpose

Define the certification workflow required before a connector can be enabled in production environments.

## Architecture-level context

Certification ensures connectors enforce the same security, data quality, and operational standards as the core platform. Evidence is attached to the connector registry and referenced by the orchestration layer before a connector can be activated.

## Certification checklist

| Step | Evidence | Artifact path |
| --- | --- | --- |
| Schema coverage | Mapping files cover required fields | `integrations/connectors/<name>/mappings/*.yaml` |
| Auth validation | Token flow tested and rotated | `config/<env>/connector-auth.yaml` |
| Sandbox tests | CRUD against vendor sandbox | `integrations/connectors/<name>/tests/` |
| Rate-limit handling | Retry policy documented | `integrations/connectors/<name>/manifest.yaml` |
| Security review | Secrets stored in vault | `docs/architecture/security-architecture.md` |
| Data lineage | Lineage artifact emitted | `data/lineage/` |

## Usage example

Record certification status in the registry:

```bash
rg -n "certification" integrations/connectors/registry/connectors.json
```

## How to verify

Ensure a connector has at least one mapping file:

```bash
ls integrations/connectors/jira/mappings
```

Expected output: mapping files such as `project.yaml`.

## Certification automation

Run the automated certification harness to validate manifests, mapping coverage, and contract tests. The command emits a report artifact used by CI:

```bash
python scripts/connector-certification.py --output artifacts/connector-certification-report.json --run-tests
```

The report includes per-connector results plus a summary status.

## Implementation status

- **Implemented**: automated certification evidence collection and report generation.
- **Maintained**: manual checklist and registry metadata for audit context.

## Related docs

- [Connector Overview](overview.md)
- [Connector Registry](../../integrations/connectors/registry/connectors.json)
- [Data Lineage](../data/lineage.md)
