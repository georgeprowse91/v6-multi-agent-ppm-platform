# Connector Hub

## Purpose

Describe the Connector Hub application and its role in the platform experience layer.

## What's inside

- [integrations/apps/connector-hub/helm](/integrations/apps/connector-hub/helm): Helm chart packaging for Kubernetes deployments.
- [integrations/apps/connector-hub/registry](/integrations/apps/connector-hub/registry): Registry assets and indexes.
- [integrations/apps/connector-hub/sandbox](/integrations/apps/connector-hub/sandbox): Sandbox assets for local or demo use.
- [integrations/apps/connector-hub/src](/integrations/apps/connector-hub/src): Implementation source for this component.
- [integrations/apps/connector-hub/tests](/integrations/apps/connector-hub/tests): Test suites and fixtures.
- [integrations/apps/connector-hub/Dockerfile](/integrations/apps/connector-hub/Dockerfile): Container build recipe for local or CI use.

## How it's used

Apps are started via `tools/component_runner` or the Makefile targets that wrap common workflows.

## How to run / develop / test

Run the app locally (dry run to see the command):

```bash
python -m tools.component_runner run --type app --name connector-hub --dry-run
```

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

## Troubleshooting

- Missing dependencies: install dev dependencies with `make install-dev`.
- Startup errors: verify required env vars are present in `.env`.
