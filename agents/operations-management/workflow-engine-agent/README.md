# Workflow Process Engine Specification

## Purpose

Define the responsibilities, workflows, and integration points for Workflow Process Engine. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Scope validation (The Workflow Engine agent)

### Intended scope
- Orchestrate workflow definitions (JSON/YAML/BPMN) into executable task graphs, persist them, and manage workflow instances (start, pause, resume, cancel).【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L90-L437】
- Coordinate task execution via a task queue, track task assignments, and manage retries/compensation logic for failed steps.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1207-L1764】
- Emit workflow events for audit/telemetry and integrate with event bus topics (workflow notifications, Azure Monitor/Event Grid).【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1351-L1512】

### Out of scope (explicit non-responsibilities)
- Source-control change governance, CI/CD policy enforcement, or repo compliance checks (belongs to the Change Control agent change configuration).【F:agents/operations-management/change-control-agent/README.md†L1-L97】
- Process mining and improvement analytics (belongs to the Continuous Improvement agent continuous improvement/process mining).【F:agents/operations-management/continuous-improvement-agent/README.md†L1-L31】
- UI ownership: this agent emits events and tasks, but does not define UI/UX workflows or render task experiences directly (no UI modules in scope).【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1351-L2017】

### Inputs
- API actions: `define_workflow`, `start_workflow`, `get_workflow_status`, `assign_task`, `complete_task`, `cancel_workflow`, `pause_workflow`, `resume_workflow`, `handle_event`, `retry_failed_task`, `get_workflow_instances`, `get_task_inbox`, `deploy_bpmn_workflow`, `upload_bpmn_workflow`.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L122-L299】
- Workflow definitions: JSON/YAML spec via `workflow_spec`/`workflow_yaml`, or BPMN 2.0 XML via `bpmn_xml`/`bpmn_path`.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L181-L307】【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L885-L939】
- Trigger events: event payloads via `handle_event` and Service Bus subscriptions (`workflow.triggers`).【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L340-L394】【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1171-L1178】

### Outputs
- Workflow definition results (workflow ID, orchestration steps, validation status).【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L319-L389】
- Workflow instance status/summary responses (status, progress, tasks).【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L439-L605】
- Task assignment/notification events and task queue messages for downstream execution.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L607-L1350】

### Decision responsibilities
- Authorization: role-based guardrails per action in `rbac_policy`.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L61-L92】【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1845-L1857】
- Workflow progression: determines next tasks based on transitions, dependencies, and conditions.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1281-L1415】
- Compensation/retry strategy: applies retry policies and triggers compensation workflows on failures/cancel events.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1168-L1764】

### Must / must-not behaviors
- Must validate workflow definitions before persisting or starting instances (name + task presence + spec parsing).【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L905-L1040】
- Must persist workflow definitions/instances/tasks to the state store before emitting events or returning success responses.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L319-L631】
- Must not start workflows or execute tasks if authorization fails (RBAC enforcement).【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1845-L1857】
- Must evaluate event payload criteria with deterministic matching semantics, including nested field-path lookups and fail-closed handling for malformed definitions.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1491-L1654】

## Handoff boundaries with the Change Control agent and the Continuous Improvement agent

### the Change Control agent (Change Configuration)
- the Change Control agent owns change requests, approvals, repo integrations, and CI/CD change status workflows. the Workflow Engine agent should only orchestrate the workflow steps once a change request is created and should receive change metadata as workflow inputs (e.g., `workflow_spec` + repository/PR metadata).【F:agents/operations-management/change-control-agent/README.md†L1-L92】【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L214-L292】
- Boundary: the Workflow Engine agent must not author or evaluate change approvals; it should create/route tasks for approvals, then await completion via `complete_task` events.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L607-L744】

### the Continuous Improvement agent (Continuous Improvement Process Mining)
- the Continuous Improvement agent consumes workflow execution events/telemetry for process mining and continuous improvement insights. the Workflow Engine agent publishes `workflow.events`/monitoring payloads which the Continuous Improvement agent can ingest.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1351-L1512】
- Boundary: the Workflow Engine agent should not analyze or optimize workflows based on historical performance; those insights should be owned by the Continuous Improvement agent and fed back via new/updated workflow definitions.【F:agents/operations-management/continuous-improvement-agent/README.md†L1-L31】

## Functional gaps, inconsistencies, and alignment needs

### Functional gaps/inconsistencies
- `retry_failed_task` marks a task as retrying but does not re-enqueue or re-run it, unlike `_mark_task_failed` which schedules retries. Align retry semantics so both paths are consistent.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L752-L792】【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1642-L1735】
- BPMN upload path reads from disk without validating file existence/size limits; add guardrails if the orchestration service exposes this to users.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L816-L835】
- Workflow completion logic excludes decision/parallel/loop tasks but depends on completed task IDs; ensure those virtual steps are not marked as required tasks in definitions or else completion checks will miscount.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1417-L1444】

### Required prompt/tool/template/connector/UI alignment
- Prompt/API: document mandatory `action` values and required fields in orchestration service docs so callers provide `workflow_id`, `instance_id`, or `bpmn_xml` as needed.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L122-L196】
- Template alignment: ensure workflow templates in `config/workflow-engine-agent/workflow_templates.yaml` follow `ppm.workflow/v1` and include `metadata`/`steps` fields consistent with `workflow_spec` parsing.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1860-L1876】【F:agents/operations-management/workflow-engine-agent/src/workflow_spec.py†L1-L122】
- Connector alignment: confirm Service Bus/Event Grid/Monitor topic names match enterprise integration catalogs; the agent publishes to `workflow.events`, `workflow.notifications`, `azure.monitor.telemetry`, and `azure.eventgrid.events`.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L1351-L1512】
- UI alignment: the UI should render task inboxes based on `get_task_inbox` outputs and handle status transitions (`assigned`, `completed`, `failed`) consistently with the agent’s task lifecycle.【F:agents/operations-management/workflow-engine-agent/src/workflow_engine_agent.py†L723-L875】

## Checkpoint

Workflow orchestration boundaries are validated and ready for execution, with remaining focus on retry semantics and template alignment confirmations.

## What's inside

- [src](/agents/operations-management/workflow-engine-agent/src): Implementation source for this component.
- [tests](/agents/operations-management/workflow-engine-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/operations-management/workflow-engine-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name workflow-engine-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/workflow-engine-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Durable workflow configuration

The agent loads durable workflow orchestration definitions from `config/workflow-engine-agent/durable_workflows.yaml` on startup. Each workflow entry defines ordered steps, retry policies, and optional compensation tasks. The agent registers these definitions as Durable Functions-style orchestrations and persists them in the workflow state store.

### Workflow specification format

The agent supports JSON or YAML workflow definitions with step-based modeling, branching logic, parallelism, and retries. Definitions can be supplied inline via `workflow_spec` or `workflow_yaml` in the API payload. Key fields:

- `apiVersion`: `ppm.workflow/v1`
- `kind`: `Workflow`
- `metadata`: name, version, owner, description
- `steps`: list of steps (`task`, `decision`, `parallel`, `approval`, `script`, `notification`, `loop`) with `next`, `branches`, and `retry` policies.

Sample templates live in `config/workflow-engine-agent/workflow_templates.yaml` and are loaded on startup.

### BPMN 2.0 support

The engine can parse BPMN 2.0 XML definitions and convert them into Durable Functions-style orchestrations. Use the `/workflows/upload` API (in the orchestration service) to upload BPMN files for deployment. BPMN user tasks become `human` tasks; service/script tasks become `automated` tasks. The parser uses `bpmn-python` when available and falls back to an XML parser.

### Database schema

When configured with a database backend, the agent persists workflow metadata in PostgreSQL tables:

- `workflow_definitions`: stores workflow definitions and metadata (`workflow_id`, name, version, JSON definition payload).
- `workflow_runs`: stores workflow instance payloads, status, and checkpoint metadata.

### Observability & integrations

The agent emits workflow events to Azure Service Bus, Azure Monitor telemetry, and Azure Event Grid topics (via the event bus wrapper). It also supports triggering Azure Logic Apps tasks and Durable Functions-style retries and compensation flows.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
