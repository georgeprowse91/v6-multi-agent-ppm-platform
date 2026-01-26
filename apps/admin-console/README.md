# Admin Console

## Purpose

Describe the Admin Console application and its role in the platform experience layer.

## What's inside

- `apps/admin-console/helm`: Helm chart packaging for Kubernetes deployments.
- `apps/admin-console/tests`: Test suites and fixtures.
- `apps/admin-console/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Apps are started via `tools/component_runner` or the Makefile targets that wrap common workflows.

## How to run / develop / test

Run the app locally (dry run to see the command):

```bash
python -m tools.component_runner run --type app --name admin-console --dry-run
```

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

## Troubleshooting

- Missing dependencies: install dev dependencies with `make install-dev`.
- Startup errors: verify required env vars are present in `.env`.
