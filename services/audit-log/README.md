# Audit Log

## Purpose

Define the Audit Log service responsibilities and how it integrates with the platform.

## What's inside

- `services/audit-log/contracts`: Service contracts and schema artifacts.
- `services/audit-log/helm`: Helm chart packaging for Kubernetes deployments.
- `services/audit-log/src`: Implementation source for this component.
- `services/audit-log/storage`: Storage backends and retention structures.
- `services/audit-log/tests`: Test suites and fixtures.
- `services/audit-log/Dockerfile`: Container build recipe for local or CI use.

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
