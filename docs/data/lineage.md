# Data Lineage

## Purpose

Explain how lineage is captured for connector syncs and agent transformations, with concrete examples.

## Architecture-level context

Lineage provides end-to-end traceability from external systems into canonical schemas. The connector runtime emits lineage artifacts in `data/lineage/` which are consumed by audit, compliance, and analytics processes.

## Lineage capture approach

- **Trigger**: every connector sync or agent write.
- **Payload**: source system, record IDs, transformations, quality score.
- **Storage**: JSON artifacts in `data/lineage/`.

## Example lineage artifact

```json
{
  "id": "lin-2026-01-15-001",
  "connector": "jira",
  "source": {"system": "jira", "object": "project"},
  "target": {"schema": "project", "record_id": "PROJ-2026-001"}
}
```

Full example: `data/lineage/example-lineage.json`.

## Usage example

View the example lineage artifact:

```bash
sed -n '1,160p' data/lineage/example-lineage.json
```

## How to verify

Confirm the example file exists:

```bash
ls data/lineage/example-lineage.json
```

Expected output: the JSON file path.

## Implementation status

- **Implemented**: example lineage artifact structure.
- **Planned**: automated lineage generation in connector runtime.

## Related docs

- [Connector Overview](../connectors/overview.md)
- [Data Quality](data-quality.md)
