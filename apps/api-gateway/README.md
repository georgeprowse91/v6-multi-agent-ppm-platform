# Api Gateway

## Purpose

Describe the Api Gateway application and its role in the platform experience layer.

## What's inside

- `apps/api-gateway/helm`: Helm chart packaging for Kubernetes deployments.
- `apps/api-gateway/openapi`: OpenAPI artifacts and generated summaries.
- `apps/api-gateway/src`: Implementation source for this component.
- `apps/api-gateway/tests`: Test suites and fixtures.
- `apps/api-gateway/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Apps are started via `tools/component_runner` or the Makefile targets that wrap common workflows.

## How to run / develop / test

Run the app locally (dry run to see the command):

```bash
python -m tools.component_runner run --type app --name api-gateway --dry-run
```

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

## Troubleshooting

- Missing dependencies: install dev dependencies with `make install-dev`.
- Startup errors: verify required env vars are present in `.env`.
