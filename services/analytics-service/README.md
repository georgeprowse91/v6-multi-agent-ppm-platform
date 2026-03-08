# Analytics Service

## Purpose

The Analytics Service app computes KPI, trend, and utilization metrics that power dashboards and reporting across the platform.

## What's inside

- [helm](/services/analytics-service/helm): Helm chart packaging for Kubernetes deployments.
- [jobs](/services/analytics-service/jobs): Job manifests and schedules.
- [models](/services/analytics-service/models): Data model definitions used by this component.
- [src](/services/analytics-service/src): Implementation source for this component.
- [tests](/services/analytics-service/tests): Test suites and fixtures.
- [Dockerfile](/services/analytics-service/Dockerfile): Container build recipe for local or CI use.

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

## Ownership and support

- Owner: Platform Engineering
- Support: #ppm-platform-support

