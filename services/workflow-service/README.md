# Workflow Service

## Purpose

The Workflow Service app executes workflow definitions, evaluates gate criteria, and records orchestration outcomes for auditability.

## What's inside

- [helm](/services/workflow-service/helm): Helm chart packaging for Kubernetes deployments.
- [migrations](/services/workflow-service/migrations): Database migration scripts and notes.
- [src](/services/workflow-service/src): Implementation source for this component.
- [tests](/services/workflow-service/tests): Test suites and fixtures.
- [workflows](/services/workflow-service/workflows): Workflow definitions and examples.
- [Dockerfile](/services/workflow-service/Dockerfile): Container build recipe for local or CI use.

## How it's used

Apps are started via `tools/component_runner` or the Makefile targets that wrap common workflows.

## How to run / develop / test

Run the app locally (dry run to see the command):

```bash
python -m tools.component_runner run --type app --name workflow-service --dry-run
```

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

## Troubleshooting

- Missing dependencies: install dev dependencies with `make install-dev`.
- Startup errors: verify required env vars are present in `.env`.

## Ownership and support

- Owner: Platform Engineering
- Support: #ppm-platform-support

