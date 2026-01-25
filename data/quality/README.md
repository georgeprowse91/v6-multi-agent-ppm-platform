# Data Quality Rules

## Purpose

Store canonical data quality rules used by the Data Synchronization & Quality agent to score and remediate incoming data.

## Architecture-level context

Rules are applied during connector sync and API writes to enforce schema completeness, validity, and consistency. Scores are emitted into lineage artifacts for auditability.

## Usage example

View the rules file:

```bash
sed -n '1,200p' data/quality/rules.yaml
```

## How to verify

Confirm the rules file exists:

```bash
ls data/quality/rules.yaml
```

Expected output: the YAML rules file path.

## Related docs

- [Data Quality](../../docs/data/data-quality.md)
- [Data Lineage](../../docs/data/lineage.md)
