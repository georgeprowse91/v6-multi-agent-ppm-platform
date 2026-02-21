# Data Sync Service

## Purpose

Define the Data Sync Service service responsibilities and how it integrates with the platform.

## Key endpoints

- [healthz](/GET /healthz): Service health check.
- [run](/POST /v1/sync/run): Run all configured sync jobs.
- [{job_id}](/GET /v1/sync/status/{job_id}): Retrieve status for a specific sync job.
- [jobs](/GET /v1/sync/jobs): List sync jobs.
- [run](/POST /v1/sync/jobs/{connector}/{entity}/run): Run a sync job for a specific connector/entity.
- [logs](/GET /v1/sync/logs): List sync logs.
- [summary](/GET /v1/sync/summary): Summary metrics across sync jobs.
- [conflicts](/GET /v1/sync/conflicts): List unresolved conflicts.

**Default port:** `8080`

## What's inside

- [contracts](/services/data-sync-service/contracts): Service contracts and schema artifacts.
- [helm](/services/data-sync-service/helm): Helm chart packaging for Kubernetes deployments.
- [rules](/services/data-sync-service/rules): Rules and constraints used by sync/validation.
- [src](/services/data-sync-service/src): Implementation source for this component.
- [tests](/services/data-sync-service/tests): Test suites and fixtures.
- [Dockerfile](/services/data-sync-service/Dockerfile): Container build recipe for local or CI use.

## How it's used

Services are run via `tools/component_runner` or Docker and are referenced by API and orchestration layers.

## How to run / develop / test

Run the service locally (dry run to inspect the command):

```bash
python -m tools.component_runner run --type service --name data-sync-service --dry-run
```

## Configuration

Service-specific environment variables should be defined in `.env` and, for production, in secrets managers.

## Troubleshooting

- Missing env vars: review the service README or source code for required settings.
- Port conflicts: adjust `PORT` or Docker/Helm values.

## Generated docs

- Endpoint reference (source of truth): [`docs/generated/services/data-sync-service.md`](../../docs/generated/services/data-sync-service.md).
- Regenerate with: `python ops/tools/codegen/generate_docs.py`.

## Ownership and support

- Owner: Platform Engineering
- Support: #ppm-platform-support

