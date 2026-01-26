# Workflow Engine

## Purpose

Describe the Workflow Engine application and its role in the platform experience layer.

## What's inside

- `apps/workflow-engine/helm`: Helm chart packaging for Kubernetes deployments.
- `apps/workflow-engine/migrations`: Database migration scripts and notes.
- `apps/workflow-engine/src`: Implementation source for this component.
- `apps/workflow-engine/tests`: Test suites and fixtures.
- `apps/workflow-engine/workflows`: Workflow definitions and examples.
- `apps/workflow-engine/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Apps are started via `tools/component_runner` or the Makefile targets that wrap common workflows.

## How to run / develop / test

Run the app locally (dry run to see the command):

```bash
python -m tools.component_runner run --type app --name workflow-engine --dry-run
```

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

## Troubleshooting

- Missing dependencies: install dev dependencies with `make install-dev`.
- Startup errors: verify required env vars are present in `.env`.
