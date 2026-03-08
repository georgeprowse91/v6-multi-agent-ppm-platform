# Applications

## Purpose

Catalog the user-facing applications and their deployment assets.

## Directory structure

| Folder | Description |
| --- | --- |
| [demo_streamlit/](./demo_streamlit/) | Streamlit-based interactive demo application with pre-loaded scenario data |
| [mobile/](./mobile/) | React Native mobile application |
| [web/](./web/) | Web console (React SPA frontend + FastAPI backend) |

Backend services (API Gateway, Orchestration Service, Workflow Service, Admin Console, Analytics Service, Document Service, Connector Hub) have moved to [`services/`](../services/).

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
