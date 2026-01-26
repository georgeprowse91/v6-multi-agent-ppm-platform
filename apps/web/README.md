# Web

## Purpose

Describe the Web application and its role in the platform experience layer.

## What's inside

- `apps/web/data`: Data assets and fixtures for this component.
- `apps/web/e2e`: End-to-end test specs or tooling.
- `apps/web/helm`: Helm chart packaging for Kubernetes deployments.
- `apps/web/public`: Static assets served by the app.
- `apps/web/scripts`: Scripts that support this component or workflow.
- `apps/web/src`: Implementation source for this component.

## How it's used

Apps are started via `tools/component_runner` or the Makefile targets that wrap common workflows.

## How to run / develop / test

Run the app locally (dry run to see the command):

```bash
python -m tools.component_runner run --type app --name web --dry-run
```

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

## Troubleshooting

- Missing dependencies: install dev dependencies with `make install-dev`.
- Startup errors: verify required env vars are present in `.env`.
