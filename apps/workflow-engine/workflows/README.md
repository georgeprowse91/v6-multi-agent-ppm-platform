# Workflow Engine: Workflows

## Purpose

Document the workflows assets for the Workflow Engine application.

## What's inside

- [definitions](/apps/workflow-engine/workflows/definitions): Subdirectory containing definitions assets for this area.
- [schema](/apps/workflow-engine/workflows/schema): Schemas or validation rules for component assets.

Sample workflow templates included:
- `change-request`
- `deployment-rollback`
- `project-initiation`
- `quality-audit`
- `risk-mitigation`

## How it's used

These assets are consumed by the parent app during build, runtime, or deployment.

## How to run / develop / test

Validate assets by listing files or running the parent app locally.

```bash
ls apps/workflow-engine/workflows
```

## Configuration

No direct configuration in this subfolder; use the parent app's `.env` settings.

## Troubleshooting

- Missing asset errors: confirm files referenced by the app exist in this folder.
- Packaging issues: ensure paths match those referenced in the parent app configuration.
