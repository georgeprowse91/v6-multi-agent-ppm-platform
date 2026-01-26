# Workflow Engine

Workflow definitions and runtime service for executing workflow instances.

## Current state

- Workflow definitions live in `apps/workflow-engine/workflows/`.
- Runtime service is implemented in `apps/workflow-engine/src/main.py` with SQLite persistence.
- Audit events emitted to the audit-log service when workflows start/update.

## Quickstart

Run the workflow engine:

```bash
uvicorn main:app --app-dir apps/workflow-engine/src --reload --port 8082
```

## How to verify

```bash
curl http://localhost:8082/healthz
```

## Key files

- `apps/workflow-engine/src/main.py`: workflow API service.
- `apps/workflow-engine/src/workflow_storage.py`: workflow persistence.
- `apps/workflow-engine/workflows/`: workflow definition YAMLs.

## Tests

```bash
pytest tests/e2e -v
```
