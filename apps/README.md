# Applications

User-facing apps and API services that make up the platform runtime.

## Apps in this repository

- **admin-console**: admin UI for tenants, permissions, and governance.
- **analytics-service**: analytics job definitions and data models.
- **api-gateway**: FastAPI entrypoint for agent queries and platform APIs.
- **connector-hub**: registry and sandbox for external connectors.
- **document-service**: document ingestion, storage, and retrieval workflows.
- **orchestration-service**: multi-agent coordinator invoked by the API gateway.
- **web**: Streamlit prototype UI.
- **workflow-engine**: workflow definitions and orchestration runtime.

## Quickstart

Run the core developer-facing apps:

```bash
make run-api
make run-prototype
```

Or start everything in Docker:

```bash
make docker-up
```

## How to verify

```bash
curl http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok","timestamp":"2024-01-01T12:00:00","version":"0.1.0"}
```

## Key files

- `apps/api-gateway/src/api/main.py`: API entrypoint.
- `apps/web/streamlit_app.py`: Streamlit prototype.
- `apps/orchestration-service/src/orchestrator.py`: agent orchestrator.
- `apps/workflow-engine/workflows/`: workflow definitions.

## Example

List the API routes module directory:

```bash
ls apps/api-gateway/src/api/routes
```
