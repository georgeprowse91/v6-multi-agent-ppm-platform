# Applications

## Purpose

Catalog the user-facing applications and their deployment assets.

## Directory structure

| Folder | Description |
| --- | --- |
| [admin-console/](./admin-console/) | Admin console application |
| [analytics-service/](./analytics-service/) | Analytics and reporting service |
| [api-gateway/](./api-gateway/) | API gateway (front door for client requests) |
| [demo_streamlit/](./demo_streamlit/) | Streamlit-based interactive demo application with pre-loaded scenario data |
| [document-service/](./document-service/) | Document storage and management service |
| [mobile/](./mobile/) | React Native mobile application |
| [orchestration-service/](./orchestration-service/) | Orchestration service for agent coordination |
| [web/](./web/) | Web console (React SPA frontend with Streamlit fallback) |
| [workflow-service/](./workflow-service/) | Workflow persistence and execution engine |

Connector Hub now lives under [`integrations/apps/connector-hub/`](../integrations/apps/connector-hub/).

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
