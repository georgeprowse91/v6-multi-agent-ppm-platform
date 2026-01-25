# Data Lineage Artifacts

## Purpose

Capture lineage evidence for every connector sync and agent-driven data transformation.

## Architecture-level context

Lineage artifacts provide traceability from external systems into canonical schemas. They are produced by the connector runtime and consumed by analytics, audit, and compliance workflows.

## Usage example

View the sample lineage artifact:

```bash
sed -n '1,200p' data/lineage/example-lineage.json
```

## How to verify

Confirm the lineage example exists:

```bash
ls data/lineage/example-lineage.json
```

Expected output: the JSON file path.

## Related docs

- [Lineage Overview](../../docs/data/lineage.md)
- [Data Quality Rules](../quality/README.md)
