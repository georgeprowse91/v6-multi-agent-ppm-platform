# Analytics Service

Analytics job definitions and models that power KPI dashboards and portfolio insights.

## Current state

- Batch/stream job specs live in `apps/analytics-service/jobs/`.
- Data models live in `apps/analytics-service/models/`.
- Validation is handled by `scripts/validate-analytics-jobs.py`.

## Quickstart

Validate the analytics job specs:

```bash
python scripts/validate-analytics-jobs.py
```

## How to verify

```bash
ls apps/analytics-service/jobs
```

Expected output includes job YAML files used by analytics pipelines.

## Key files

- `apps/analytics-service/jobs/`: job definitions.
- `apps/analytics-service/models/`: analytics data models.
- `scripts/validate-analytics-jobs.py`: validation entrypoint.

## Example

List analytics model names:

```bash
rg -n "model" apps/analytics-service/models
```

## Next steps

- Add execution runners under `apps/analytics-service/src/`.
- Wire outputs into `services/telemetry-service/` for storage and reporting.
