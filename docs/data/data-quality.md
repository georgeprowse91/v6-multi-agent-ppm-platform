# Data Quality

## Purpose

Define the quality scoring approach for canonical data and provide example rules used during connector sync.

## Architecture-level context

Data quality scoring is executed by the Data Synchronization & Quality agent (Agent 23). Rules are stored in `data/quality/rules.yaml` and applied to incoming data before it is persisted. Scores are captured in lineage artifacts for auditability.

## Quality dimensions

- **Completeness**: required fields are present.
- **Validity**: values match expected formats or ranges.
- **Consistency**: values align with canonical enums and references.
- **Timeliness**: data freshness meets sync policy.

## Example rules

```yaml
- id: project-required-fields
  entity: project
  checks:
    - field: project.id
      type: required
```

Full rule set: `data/quality/rules.yaml`.

## Usage example

View the rules file:

```bash
sed -n '1,120p' data/quality/rules.yaml
```

## How to verify

Confirm the rule file exists:

```bash
ls data/quality/rules.yaml
```

Expected output: the YAML rules file path.

## Implementation status

- **Implemented**: baseline rules and scoring weights.
- **Implemented**: automated remediation workflows with API-triggered fixes in the lineage service.

## Related docs

- [Data Model](data-model.md)
- [Data Lineage](lineage.md)
