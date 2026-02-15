# Analytics Service

## Purpose

Describe the Analytics Service application and its role in the platform experience layer.

## What's inside

- [helm](/apps/analytics-service/helm): Helm chart packaging for Kubernetes deployments.
- [jobs](/apps/analytics-service/jobs): Job manifests and schedules.
- [models](/apps/analytics-service/models): Data model definitions used by this component.
- [src](/apps/analytics-service/src): Implementation source for this component.
- [tests](/apps/analytics-service/tests): Test suites and fixtures.
- [Dockerfile](/apps/analytics-service/Dockerfile): Container build recipe for local or CI use.

## How it's used

Apps are started via `tools/component_runner` or the Makefile targets that wrap common workflows.

## How to run / develop / test

Run the app locally (dry run to see the command):

```bash
python -m tools.component_runner run --type app --name analytics-service --dry-run
```

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

## Troubleshooting

- Missing dependencies: install dev dependencies with `make install-dev`.
- Startup errors: verify required env vars are present in `.env`.
