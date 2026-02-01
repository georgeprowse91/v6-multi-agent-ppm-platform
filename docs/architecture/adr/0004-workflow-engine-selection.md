# ADR 0004: Workflow Engine Selection

## Status

Accepted.

## Context

The platform needs durable workflow execution for stage gates, approvals, and orchestration of agent tasks. A minimal in-repo workflow engine is required for local development and deterministic testing.

## Decision

Implement a focused workflow engine in `apps/workflow-engine` using FastAPI and SQLite-backed storage. Workflow definitions are YAML files stored under `apps/workflow-engine/workflows/definitions/` and discovered via a registry.

To support distributed execution, introduce a Celery-backed workflow runtime that dispatches each workflow step as an idempotent Celery task. Celery uses Redis or RabbitMQ as the broker and handles asynchronous task orchestration, while the workflow engine persists state in SQLite (or a future external store) and exposes workflow lifecycle APIs. The new shared package `packages/workflow` defines workflow dispatchers, task definitions, and result aggregation for worker pools.

## Consequences

- Provides a deterministic workflow engine for local development and CI.
- Keeps workflow definitions versioned in Git.
- Enables distributed execution across agents and services by enqueueing steps on Celery workers.
- Adds operational dependencies for a broker (Redis or RabbitMQ) and a Celery worker pool.
- Requires idempotent workflow steps and explicit state persistence to support retries.

## References

- `apps/workflow-engine/src/main.py`
- `apps/workflow-engine/src/workflow_storage.py`
- `apps/workflow-engine/workflows/definitions`
- `packages/workflow/src/workflow`
- `docs/architecture/workflow-architecture.md`
