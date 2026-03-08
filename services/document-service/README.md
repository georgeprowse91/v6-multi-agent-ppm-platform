# Document Service

## Purpose

The Document Service app stores and serves project artifacts, supports versioning workflows, and enforces document policy controls.

## What's inside

- [helm](/services/document-service/helm): Helm chart packaging for Kubernetes deployments.
- [migrations](/services/document-service/migrations): Database migration scripts and notes.
- [policies](/services/document-service/policies): Policy definitions enforced by the platform.
- [src](/services/document-service/src): Implementation source for this component.
- [tests](/services/document-service/tests): Test suites and fixtures.
- [Dockerfile](/services/document-service/Dockerfile): Container build recipe for local or CI use.

## How it's used

Apps are started via `tools/component_runner` or the Makefile targets that wrap common workflows.

## How to run / develop / test

Run the app locally (dry run to see the command):

```bash
python -m tools.component_runner run --type app --name document-service --dry-run
```

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

## Troubleshooting

- Missing dependencies: install dev dependencies with `make install-dev`.
- Startup errors: verify required env vars are present in `.env`.

## Ownership and support

- Owner: Platform Engineering
- Support: #ppm-platform-support

