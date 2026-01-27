# ADR 0004: Workflow Engine Selection

## Status

Accepted.

## Context

The platform needs durable workflow execution for stage gates, approvals, and orchestration of agent tasks. A minimal in-repo workflow engine is required for local development and deterministic testing.

## Decision

Implement a lightweight workflow engine in `apps/workflow-engine` using FastAPI and SQLite-backed storage. Workflow definitions are YAML files stored under `apps/workflow-engine/workflows/definitions/` and discovered via a registry.

## Consequences

- Provides a deterministic workflow engine for local development and CI.
- Keeps workflow definitions versioned in Git.
- Requires future work to support distributed execution and external backing stores.

## References

- `apps/workflow-engine/src/main.py`
- `apps/workflow-engine/src/workflow_storage.py`
- `apps/workflow-engine/workflows/definitions`
- `docs/architecture/workflow-architecture.md`
