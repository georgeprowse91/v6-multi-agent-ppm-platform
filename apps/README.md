# Applications

## Purpose

Catalog the user-facing applications and their deployment assets.

## What's inside

- `apps/admin-console`: Subdirectory containing admin console assets for this area.
- `apps/analytics-service`: Subdirectory containing analytics service assets for this area.
- `apps/api-gateway`: Subdirectory containing api gateway assets for this area.
- `apps/connector-hub`: Subdirectory containing connector hub assets for this area.
- `apps/document-service`: Subdirectory containing document service assets for this area.
- `apps/orchestration-service`: Subdirectory containing orchestration service assets for this area.

## How it's used

Apps are runnable via `tools/component_runner` and deployed using Helm charts under each app folder.

## How to run / develop / test

List available apps and run one locally:

```bash
python -m tools.component_runner list --type app
python -m tools.component_runner run --type app --name api-gateway --dry-run
```

## Configuration

Apps rely on `.env` and config files under `config/` for tenant and environment settings.

## Troubleshooting

- No runnable entrypoint detected: ensure each app has `src/main.py` or a Dockerfile.
- Port conflicts: check the port mappings in the app Dockerfile or FastAPI config.
