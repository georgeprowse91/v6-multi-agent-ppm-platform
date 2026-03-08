# Orchestration Service

## Purpose

The Orchestration Service app coordinates multi-agent workflows, applies routing policies, and tracks execution state transitions.

## What's inside

- [helm](/services/orchestration-service/helm): Helm chart packaging for Kubernetes deployments.
- [planners](/services/orchestration-service/planners): Planning templates and orchestration hints.
- [policies](/services/orchestration-service/policies): Policy definitions enforced by the platform.
- [src](/services/orchestration-service/src): Implementation source for this component.
- [tests](/services/orchestration-service/tests): Test suites and fixtures.
- [Dockerfile](/services/orchestration-service/Dockerfile): Container build recipe for local or CI use.

## How it's used

Apps are started via `tools/component_runner` or the Makefile targets that wrap common workflows.

## How to run / develop / test

Run the app locally (dry run to see the command):

```bash
python -m tools.component_runner run --type app --name orchestration-service --dry-run
```

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

## Troubleshooting

- Missing dependencies: install dev dependencies with `make install-dev`.
- Startup errors: verify required env vars are present in `.env`.

## Ownership and support

- Owner: Platform Engineering
- Support: #ppm-platform-support

