# Telemetry Service

## Purpose

Define the Telemetry Service service responsibilities and how it integrates with the platform.

## Key endpoints

- [GET /healthz](/GET /healthz): Service health check.
- [POST /v1/telemetry/ingest](/POST /v1/telemetry/ingest): Ingest telemetry events.

**Default port:** `8080`

## What's inside

- [services/telemetry-service/contracts](/services/telemetry-service/contracts): Service contracts and schema artifacts.
- [services/telemetry-service/helm](/services/telemetry-service/helm): Helm chart packaging for Kubernetes deployments.
- [services/telemetry-service/pipelines](/services/telemetry-service/pipelines): Pipeline definitions for telemetry ingestion.
- [services/telemetry-service/src](/services/telemetry-service/src): Implementation source for this component.
- [services/telemetry-service/tests](/services/telemetry-service/tests): Test suites and fixtures.
- [services/telemetry-service/Dockerfile](/services/telemetry-service/Dockerfile): Container build recipe for local or CI use.

## How it's used

Services are run via `tools/component_runner` or Docker and are referenced by API and orchestration layers.

## How to run / develop / test

Run the service locally (dry run to inspect the command):

```bash
python -m tools.component_runner run --type service --name telemetry-service --dry-run
```

## Configuration

Service-specific environment variables should be defined in `.env` and, for production, in secrets managers.

## Troubleshooting

- Missing env vars: review the service README or source code for required settings.
- Port conflicts: adjust `PORT` or Docker/Helm values.
