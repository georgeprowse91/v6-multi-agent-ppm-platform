# Data Quality Package

Shared validation and data quality helpers intended for analytics pipelines.

## Current state

- No implementation code yet in `packages/data-quality/`.
- Analytics job definitions live under `apps/analytics-service/jobs/`.

## Quickstart

Validate analytics job specs:

```bash
python scripts/validate-analytics-jobs.py
```

## How to verify

```bash
ls apps/analytics-service/jobs
```

Expected output lists analytics job YAML files.

## Key files

- `apps/analytics-service/jobs/`: analytics job definitions.
- `packages/data-quality/README.md`: scope and next steps.

## Example

Search for quality checks in analytics jobs:

```bash
rg -n "quality|validation" apps/analytics-service/jobs
```

## Next steps

- Implement data quality rules under `packages/data-quality/src/`.
- Integrate checks into analytics runners.
