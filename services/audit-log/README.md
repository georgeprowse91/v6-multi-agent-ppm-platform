# Audit Log

## Purpose

Define the Audit Log service responsibilities and how it integrates with the platform.

## Key endpoints

- [GET /healthz](/GET /healthz): Service health check.
- [POST /v1/audit/events](/POST /v1/audit/events): Ingest a new audit event (validated against schema).
- [GET /v1/audit/events/{event_id}](/GET /v1/audit/events/{event_id}): Retrieve a single audit event.

**Default port:** `8080`

## What's inside

- [services/audit-log/contracts](/services/audit-log/contracts): Service contracts and schema artifacts.
- [services/audit-log/helm](/services/audit-log/helm): Helm chart packaging for Kubernetes deployments.
- [services/audit-log/src](/services/audit-log/src): Implementation source for this component.
- [services/audit-log/storage](/services/audit-log/storage): Storage backends and retention structures.
- [services/audit-log/tests](/services/audit-log/tests): Test suites and fixtures.
- [services/audit-log/Dockerfile](/services/audit-log/Dockerfile): Container build recipe for local or CI use.

## How it's used

Services are run via `tools/component_runner` or Docker and are referenced by API and orchestration layers.

## How to run / develop / test

Run the service locally (dry run to inspect the command):

```bash
python -m tools.component_runner run --type service --name audit-log --dry-run
```

## Configuration

Service-specific environment variables should be defined in `.env` and, for production, in secrets managers.

## Troubleshooting

- Missing env vars: review the service README or source code for required settings.
- Port conflicts: adjust `PORT` or Docker/Helm values.
