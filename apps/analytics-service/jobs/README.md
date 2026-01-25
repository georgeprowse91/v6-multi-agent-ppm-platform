# Analytics Job Manifests

## Purpose
This folder stores batch job manifests executed by the analytics service. Manifests describe
schedules, inputs, outputs, and transformation steps that the orchestration service can trigger.
The manifest directory is referenced by `apps/analytics-service/job_registry.py`.

## Responsibilities
- Define repeatable analytics jobs and their schedules.
- Capture input/output datasets and transformation steps.
- Provide validated job manifests for pipeline execution.

## Folder structure
```
apps/analytics-service/jobs/
├── README.md
├── manifests/
│   └── daily-portfolio-rollup.yaml
└── schema/
    └── job-manifest.schema.json
```

## Conventions
- Manifests use `apiVersion: ppm.jobs/v1` and `kind: AnalyticsJob`.
- `metadata.name` should be kebab-case and unique.
- `schedule.cron` uses UTC unless specified otherwise.

## How to add a new job
1. Copy `manifests/daily-portfolio-rollup.yaml` and update `metadata` and `schedule`.
2. Add or update `inputs`, `outputs`, and `steps` for the new pipeline.
3. Validate the manifest with the script below.
4. Confirm the new file is picked up by `apps/analytics-service/job_registry.py`.

## How to validate/test
```bash
python scripts/validate-analytics-jobs.py apps/analytics-service/jobs/manifests/daily-portfolio-rollup.yaml
```

## Example
```yaml
apiVersion: ppm.jobs/v1
kind: AnalyticsJob
metadata:
  name: daily-portfolio-rollup
  owner: analytics-service
  version: "1.0.0"
schedule:
  cron: "0 2 * * *"
  timezone: "UTC"
```
