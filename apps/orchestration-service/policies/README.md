# Orchestration Service: Policies

## Purpose

Document the policies assets for the Orchestration Service application.

## What's inside

- `apps/orchestration-service/policies/bundles`: Subdirectory containing bundles assets for this area.
- `apps/orchestration-service/policies/schema`: Schemas or validation rules for component assets.

## How it's used

These assets are consumed by the parent app during build, runtime, or deployment.

## How to run / develop / test

Validate assets by listing files or running the parent app locally.

```bash
ls apps/orchestration-service/policies
```

## Configuration

No direct configuration in this subfolder; use the parent app's `.env` settings.

## Troubleshooting

- Missing asset errors: confirm files referenced by the app exist in this folder.
- Packaging issues: ensure paths match those referenced in the parent app configuration.
