# Services

## Purpose

Catalog backend services that power data sync, policy enforcement, and telemetry.

## What's inside

- `services/audit-log`: Subdirectory containing audit log assets for this area.
- `services/data-sync-service`: Subdirectory containing data sync service assets for this area.
- `services/data-lineage-service`: Subdirectory containing data lineage service assets for this area.
- `services/data-service`: Subdirectory containing data service assets for this area.
- `services/identity-access`: Subdirectory containing identity access assets for this area.
- `services/notification-service`: Subdirectory containing notification service assets for this area.
- `services/policy-engine`: Subdirectory containing policy engine assets for this area.
- `services/telemetry-service`: Subdirectory containing telemetry service assets for this area.

## How it's used

Services are discovered by `tools/component_runner` and deployed via Helm and Terraform resources under `infra/`.

## How to run / develop / test

List services and run one locally:

```bash
python -m tools.component_runner list --type service
python -m tools.component_runner run --type service --name audit-log --dry-run
```

## Configuration

Services use shared `.env` settings plus service-specific env vars documented in each service README.

## Troubleshooting

- Service not listed: ensure the service folder exists under `services/`.
- Startup errors: confirm database and external service endpoints are reachable.
