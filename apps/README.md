# Applications

This directory contains the user-facing applications and service-facing APIs that make up the
Multi-Agent PPM Platform runtime.

## Apps in this repository
- **admin-console**: Administrative UI for tenant setup, permissions, and governance.
- **analytics-service**: Batch/stream analytics jobs that power KPI dashboards.
- **api-gateway**: FastAPI entrypoint for agent queries and platform APIs.
- **connector-hub**: Registry and management surface for external connectors.
- **document-service**: Document ingestion, storage, and retrieval workflows.
- **orchestration-service**: Central coordination for multi-agent workflows.
- **web**: Web prototype and demo UI (Streamlit-based today).
- **workflow-engine**: Workflow definitions and orchestration runtime.

## How to run locally
Use the root Makefile targets (e.g., `make run-api`, `make run-prototype`) or Docker Compose
(`make docker-up`). See the root [README](../README.md) for details.
