# Workflow Architecture

## Purpose

Explain how durable workflows are defined, executed, and audited across the platform.

## Architecture-level context

Workflows are the backbone for stage-gate execution, approvals, and multi-step orchestration. The platform uses a dedicated workflow service service (`apps/workflow-service`) and the Approval Workflow agent (`agents/core-orchestration/approval-workflow-agent`) to execute workflow instances, persist state in an external database, and emit audit entries to the audit log service. Orchestration services and agents call the workflow service to start, resume, and inspect workflow runs while worker nodes pull tasks from a shared queue.

## Core components

| Component | Location | Responsibility |
| --- | --- | --- |
| Workflow engine API | `apps/workflow-service/src/main.py` | REST API for workflow lifecycle (start/status/resume). |
| Approval Workflow agent | `agents/core-orchestration/approval-workflow-agent/src/approval_workflow_agent.py` | Orchestrates workflow execution, approval chains, and task routing across worker nodes. |
| Workflow storage | `agents/core-orchestration/approval-workflow-agent/src/workflow_state_store.py` | External database-backed state store for workflow definitions, instances, and tasks. |
| Workflow task queue | `agents/core-orchestration/approval-workflow-agent/src/workflow_task_queue.py` | Queue-backed coordination for distributing workflow tasks to workers. |
| Workflow definitions | `apps/workflow-service/workflows/definitions/*.workflow.yaml` | Declarative workflow definitions. |
| Workflow registry | `apps/workflow-service/workflow_registry.py` | Discovery of workflow definitions. |
| Orchestration service | `apps/orchestration-service/src/main.py` | Calls workflow service and coordinates agent plans. |

## Workflow lifecycle

1. **Start**: Clients POST to `/v1/workflows/start` with a workflow ID and payload.
2. **Persist**: The workflow service stores a `run_id`, `workflow_id`, `tenant_id`, status, and payload in PostgreSQL (or another external database).
3. **Distribute**: Workflow tasks are enqueued to a shared message queue for worker nodes.
4. **Resume**: Orchestration services call `/v1/workflows/resume/{run_id}` or workers resume from persisted state after failures.
5. **Audit**: Workflow changes are emitted to the audit log for retention and compliance.

## Workflow definitions and fields

Workflow definitions live in `apps/workflow-service/workflows/definitions/*.workflow.yaml` and follow the schema below.

| Field | Description |
| --- | --- |
| `apiVersion` | Workflow API version (currently `ppm.workflows/v1`). |
| `kind` | Resource kind (`Workflow`). |
| `metadata.name` | Workflow identifier used by `/v1/workflows/start`. |
| `metadata.version` | Version string for the workflow. |
| `metadata.owner` | Owning service or agent. |
| `metadata.description` | Human-readable description. |
| `steps[].id` | Unique step identifier. |
| `steps[].type` | Step type (`task`, `decision`, `approval`, `notification`). |
| `steps[].next` | Next step ID (null ends the workflow). |
| `steps[].config` | Step-specific config (agent/action or channel/message). |
| `steps[].branches` | Decision branches with conditions and next steps. |
| `steps[].default_next` | Fallback next step for decisions. |
| `steps[].timeout_seconds` | Timeout window for approvals. |

### Available workflows

| Workflow | Purpose | Key steps |
| --- | --- | --- |
| `intake-triage` | Route new intake requests to the appropriate agent and notify owners. | `capture-intake` → `evaluate-risk` → `notify-owner` |
| `Publish Charter` | Draft and approve a project charter before publishing. | `draft_charter` → `approval_gate` → `publish_charter` |

## Failure handling and retries

- Workflows persist state in an external database, allowing the system to resume across nodes after process restarts.
- Retry policies are enforced by orchestration logic and the workflow service status transitions.
- Worker failures are handled by marking tasks failed and leaving state in the database for retry or manual intervention.

## Operational guidance

- **State backend**: Set `WORKFLOW_DATABASE_URL` and `WORKFLOW_STATE_BACKEND=db` to enable PostgreSQL persistence.
- **Queue backend**: Set `WORKFLOW_QUEUE_BACKEND=rabbitmq` and `WORKFLOW_QUEUE_URL` to enable task distribution.
- **Tenant enforcement**: The workflow service enforces tenant ownership on reads and resumes.
- **Workflow updates**: Version workflow definitions as new YAML files and update registry usage in orchestration services.

## Verification steps

- Inspect workflow definitions:
  ```bash
  ls apps/workflow-service/workflows/definitions
  ```
- Check workflow service routes:
  ```bash
  rg -n "workflows" apps/workflow-service/src/main.py
  ```
- Verify workflow instance storage includes tenant_id:
  ```bash
  rg -n "tenant_id" apps/workflow-service/src/workflow_storage.py
  ```

## Implementation status

- **Implemented:** Workflow engine API, external database-backed storage, queue-driven task distribution, YAML workflow definitions.

## Related docs

- [Agent Orchestration](agent-orchestration.md)
- [Deployment Architecture](deployment-architecture.md)
- [Runbook: Quickstart](../runbooks/quickstart.md)
