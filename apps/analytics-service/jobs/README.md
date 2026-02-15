# Analytics Service: Jobs

## Purpose

Document the jobs assets for the Analytics Service application.

## What's inside

- [apps/analytics-service/jobs/manifests](/apps/analytics-service/jobs/manifests): Kubernetes or job manifests stored here.
- [apps/analytics-service/jobs/schema](/apps/analytics-service/jobs/schema): Schemas or validation rules for component assets.

## How it's used

These assets are consumed by the parent app during build, runtime, or deployment.

## How to run / develop / test

Validate assets by listing files or running the parent app locally.

```bash
ls apps/analytics-service/jobs
```

## Configuration

No direct configuration in this subfolder; use the parent app's `.env` settings.

## Troubleshooting

- Missing asset errors: confirm files referenced by the app exist in this folder.
- Packaging issues: ensure paths match those referenced in the parent app configuration.
