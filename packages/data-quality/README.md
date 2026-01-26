# Data Quality Package

Shared validation and data quality helpers used across analytics and integration workflows.

## What this provides

- JSON Schema validation helpers (Draft 2020-12).
- Deterministic data quality rules for core domain records (projects, budgets, risks, issues, work items).
- Typed reports that list rule violations for each record.

## Usage

Validate a record with schema + business rules:

```python
from data_quality.rules import evaluate_quality_rules

report = evaluate_quality_rules("project", project_payload)
if not report.is_valid:
    for issue in report.issues:
        print(issue.rule_id, issue.message)
```

## Key files

- `packages/data-quality/src/data_quality/schema_validation.py`: JSON Schema validation helpers.
- `packages/data-quality/src/data_quality/rules.py`: executable data quality rules.

## Verification

Run tests to confirm data quality rules and schema validation behavior:

```bash
pytest tests/test_data_quality_rules.py -v
```
