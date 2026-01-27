# Workflow Architecture

## Purpose

Explain how durable workflows are defined, executed, and audited across the platform.

## Architecture-level context

Workflows are the backbone for stage-gate execution, approvals, and multi-step orchestration. The platform uses a dedicated workflow engine (`apps/workflow-engine`) that stores workflow instances, exposes REST endpoints, and emits audit entries to the audit log service. Orchestration services and agents call the workflow engine to start, resume, and inspect workflow runs.

## Core components

| Component | Location | Responsibility |
| --- | --- | --- |
| Workflow engine API | `apps/workflow-engine/src/main.py` | REST API for workflow lifecycle (start/status/resume). |
| Workflow storage | `apps/workflow-engine/src/workflow_storage.py` | Durable state store for workflow instances. |
| Workflow definitions | `apps/workflow-engine/workflows/definitions/*.workflow.yaml` | Declarative workflow definitions. |
| Workflow registry | `apps/workflow-engine/workflow_registry.py` | Discovery of workflow definitions. |
| Orchestration service | `apps/orchestration-service/src/main.py` | Calls workflow engine and coordinates agent plans. |

## Workflow lifecycle

1. **Start**: Clients POST to `/workflows/start` with a workflow ID and payload.
2. **Persist**: The workflow engine stores a `run_id`, `workflow_id`, `tenant_id`, status, and payload in SQLite.
3. **Resume**: Orchestration services call `/workflows/resume/{run_id}` to continue execution.
4. **Audit**: Workflow changes are emitted to the audit log for retention and compliance.

## Failure handling and retries

- Workflows persist state in SQLite by default, allowing the system to resume after process restarts.
- Retry policies are enforced by orchestration logic and the workflow engine status transitions.
- Long-running workflows should checkpoint through the orchestration service and record progress metadata.

## Operational guidance

- **Storage path**: Set `WORKFLOW_DB_PATH` to override the default SQLite location.
- **Tenant enforcement**: The workflow engine enforces tenant ownership on reads and resumes.
- **Workflow updates**: Version workflow definitions as new YAML files and update registry usage in orchestration services.

## Verification steps

- Inspect workflow definitions:
  ```bash
  ls apps/workflow-engine/workflows/definitions
  ```
- Check workflow engine routes:
  ```bash
  rg -n "workflows" apps/workflow-engine/src/main.py
  ```
- Verify workflow instance storage includes tenant_id:
  ```bash
  rg -n "tenant_id" apps/workflow-engine/src/workflow_storage.py
  ```

## Implementation status

- **Implemented:** Workflow engine API, SQLite-backed storage, YAML workflow definitions.
- **Planned:** Distributed workflow orchestration and external state backends.

## Related docs

- [Agent Orchestration](agent-orchestration.md)
- [Deployment Architecture](deployment-architecture.md)
- [Runbook: Quickstart](../runbooks/quickstart.md)
