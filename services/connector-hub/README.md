# Connector Hub

**Owner:** Platform Engineering
**Support:** platform-engineering@example.com

## Purpose

The Connector Hub is a FastAPI application that provides a centralized management interface for the platform's 40 integration connectors. It exposes endpoints for browsing connector status, triggering sync jobs, managing field-mapping overrides, and surfacing connector maturity and health metrics to the web console and admin workflows.

## What's inside

- [helm](/services/connector-hub/helm): Helm chart packaging for Kubernetes deployments.
- [registry](/services/connector-hub/registry): Registry assets and indexes.
- [sandbox](/services/connector-hub/sandbox): Sandbox assets for local or demo use.
- [src](/services/connector-hub/src): Implementation source for this component.
- [tests](/services/connector-hub/tests): Test suites and fixtures.
- [Dockerfile](/services/connector-hub/Dockerfile): Container build recipe for local or CI use.

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
