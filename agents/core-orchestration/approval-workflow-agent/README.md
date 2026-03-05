# Approval Workflow Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Approval Workflow Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

The Approval Workflow agent is the platform's canonical orchestration authority for long-running, multi-step workflows — including human approval chains, automated task sequences, event-driven process automation, and governed business processes. It defines, executes, monitors, and audits every structured process in the platform through a single unified engine.

Approvals are represented as a workflow pattern (`approval_gate` step type) within the workflow specification. This means every approval chain — sequential or parallel — is defined and executed as a first-class workflow, sharing the same execution engine, state persistence, audit trail, and monitoring infrastructure as any other automated process.

## Intended scope

### Responsibilities

#### Workflow engine capabilities
- **Workflow definition:** Define workflows via YAML/JSON spec (`ppm.workflow/v1`) and/or BPMN 2.0 import/export. Each workflow specifies steps, step types (`human_task`, `automated_action`, `approval_gate`, `notification`, `decision`, `parallel`, `loop`), transition conditions, retry policies, and versioning metadata.
- **Workflow instance management:** Start, pause, resume, cancel, and retry workflow instances. Each instance maintains its own execution state, tracking completed steps, step data, and current status.
- **Parallel execution and conditional logic:** Execute parallel branches within workflows and evaluate decision conditions (equality, comparison, containment, existence) against workflow data to route execution. Parallel branches are collected at join points before the workflow continues.
- **Human task inbox:** When a workflow reaches a step requiring human action, the agent creates a task in the assigned user's inbox with full context, a deadline, and relevant data from prior steps. Users can view, filter, and complete pending tasks from the platform's Task Inbox.
- **Retry policies and compensation:** When a workflow step fails, the agent applies configured retry policies (delay, exponential backoff). If a workflow fails irrecoverably, compensation workflows can be triggered to reverse completed actions and restore consistency.
- **Event-driven triggers and subscriptions:** Workflows can be triggered or advanced by events from other agents and systems. The agent monitors event subscriptions and, when a matching event arrives, triggers the appropriate action — starting a new instance, advancing a waiting step, or branching based on event data.
- **Workflow versioning:** Workflow definitions are versioned. In-flight instances continue on the version they were started with; new instances use the latest published version.
- **Workflow monitoring and reporting:** Track instance counts, success rates, average execution time, step-level performance metrics, backlog depth, and failure rates. This data feeds into the Workflow Monitoring view and the Continuous Improvement agent's process analysis.

#### Approval workflow capabilities
- **Approval chains:** Create and manage approval chains (sequential and parallel) with configurable chain types and deadlines.
- **Role-based routing and dynamic approver resolution:** Route approval requests to the correct approvers based on role mappings, organisational hierarchy, and request attributes.
- **Delegation, reminders, and escalations:** Support approver delegation with time-windowed rules, automated reminders at configurable intervals, and escalation to next-tier approvers when SLAs are breached.
- **SLA tracking:** Dynamically compute escalation deadlines from risk and criticality context, track SLA compliance, and report on approval cycle times.
- **Multi-channel notification delivery:** Deliver approval notifications via email, Teams, Slack, and push channels with deep links using "View request" language. Support locale-aware templates and accessibility formats.
- **Immutable decision records:** Record every approval decision with actor, timestamp, comments, and outcome. Decision records are append-only and form part of the immutable audit trail.
- **"My approvals" queue:** Support listing, filtering, opening, and deciding on pending approvals from a personal queue view.
- **Audit logging:** Log every approval lifecycle transition (requested, assigned, delegated, reminded, escalated, decided, closed) as a structured audit event.

### Inputs
- Workflow definition payloads (YAML/JSON `ppm.workflow/v1` or BPMN 2.0 XML).
- Workflow instance start requests with `workflow_id`, `input_data`, and optional `correlation_id`.
- Approval request payloads with `request_type`, `request_id`, `requester`, `details`, and optional `context`.
- Approval decisions with `approval_id`, `decision`, `approver_id`, and optional `comments/context`.
- Event payloads from other agents triggering workflow transitions.
- Notification preference actions (`subscribe`, `unsubscribe`, `update`, `interaction`).

### Outputs
- Workflow definitions: versioned, structured specifications of business processes.
- Workflow instances: running and completed process executions with full state history.
- Task inbox items: human tasks with context, deadlines, and workflow linkage.
- Approval chain metadata (approvers, chain type, deadline, status).
- Execution logs: step-by-step records of every workflow execution with outcomes and timestamps.
- Compensation records: documentation of rollback actions taken when workflows fail.
- Notification dispatch attempts and escalation scheduling.
- Workflow performance metrics: execution time, success rate, step-level performance by workflow type.
- Audit and analytics events for workflows, approvals, and decisions.

### Decision responsibilities
- Workflow step routing based on transition conditions and decision logic.
- Approver routing and delegation resolution.
- Escalation timing and notification delivery strategy.
- Retry and compensation strategy for failed steps.
- Approval state transitions (`pending`, `approved`, `rejected`) as recorded in the approval store.
- Workflow state transitions (`running`, `paused`, `completed`, `failed`, `cancelled`).

### Must / must-not behaviors
- **Must** validate workflow definitions against `ppm.workflow/v1` schema before execution.
- **Must** persist workflow instance state, task inbox entries, and approval decision records.
- **Must** emit events for every workflow and approval state change.
- **Must** enforce configured escalation policies and SLA deadlines.
- **Must not** reclassify intent; it assumes intent is already validated by the Intent Router agent.
- **Must not** craft user-facing narrative responses; it returns workflow/approval metadata and events for the Response Orchestration agent to present.
- **Must not** execute lifecycle transitions or enforce governance gates beyond recording decisions and escalation.

## Overlap & handoff boundaries

### Intent Router
- **Overlap risk**: routing of approval-intent and workflow-intent requests.
- **Boundary**: The Intent Router agent routes approval-intent and workflow-intent requests here based on intent routing. The Approval Workflow agent does not reclassify intent; it assumes intent is already validated.

### Response Orchestration
- **Overlap risk**: the Response Orchestration agent may request approval creation, decision recording, or workflow execution when assembling responses.
- **Boundary**: The Approval Workflow agent does not craft user-facing narrative responses; it returns workflow/approval metadata and events for the Response Orchestration agent to present.

### Change Control
- **Overlap risk**: change-triggered workflows overlap with workflow orchestration.
- **Boundary**: Change-triggered workflows are defined and executed by this agent. The Change Control agent submits workflow start requests when a change request requires a structured review process. The Approval Workflow agent executes the workflow; the Change Control agent owns the change record and impact assessment.

### Data Synchronisation
- **Overlap risk**: sync retry workflows overlap with workflow orchestration.
- **Boundary**: The Data Synchronisation agent submits workflow start requests for retry sequences. The Approval Workflow agent manages the retry workflow execution; the Data Synchronisation agent owns the sync state and mapping logic.

### Continuous Improvement
- **Overlap risk**: both agents operate on process models.
- **Boundary**: Workflow execution data (instance counts, step timings, failure rates) is consumed by the Continuous Improvement agent for process mining and improvement analysis. The Approval Workflow agent provides execution telemetry; the Continuous Improvement agent owns analysis and recommendations.

### Lifecycle Governance
- **Overlap risk**: approval events feed governance decisions.
- **Boundary**: Approval events (`approval.created`, `approval.decision`, `approval.approved/rejected`) and workflow events are published for governance agents to act on. The Approval Workflow agent does not execute lifecycle transitions or enforce governance gates beyond recording decisions and escalation.

### Workspace Setup
- **Overlap risk**: provisioning actions may require approval.
- **Boundary**: The Workspace Setup agent routes provisioning actions through this agent when organisational policy requires approval before creating or linking external assets. The Approval Workflow agent processes the approval request; the Workspace Setup agent owns the provisioning logic.

## Functional gaps / inconsistencies & alignment needs

- Approval gate definitions must be aligned with governance stage gates (the Lifecycle Governance agent) and intent routing schema (the Intent Router agent).
- Workflow definitions must be validated against `ppm.workflow/v1` schema before execution.
- Notification templates and escalation timing must align with UI and notification service capabilities.
- Event payload schemas must remain compatible with Event Bus and analytics consumers.
- BPMN import must map standard BPMN elements to the platform's step types; unsupported elements should produce clear validation errors.
- Prompting, tool schemas, and UI should use the same approval decision vocabulary (`pending`, `approved`, `rejected`) and workflow status vocabulary (`running`, `paused`, `completed`, `failed`, `cancelled`), and include `approval_id`, `workflow_id`, `tenant_id`, and `correlation_id` where applicable.

## Checkpoint: approval gate definitions

| Gate | Trigger | Required inputs | Output |
| --- | --- | --- | --- |
| **Approval requested** | New approval request | `request_type`, `request_id`, `requester`, `details` | Approval chain + `approval_id`, status `pending` |
| **Decision recorded** | Approver submits decision | `approval_id`, `decision`, `approver_id`, optional `comments` | Stored decision + audit/event emission |
| **Escalation fired** | SLA timeout reached | Approval chain + escalation policy | Reminder notifications + escalation audit/event |
| **Approval closed** | Decision is `approved` or `rejected` | `approval_id`, decision | Finalized status + downstream governance events |

### Workflow step types

| Step type | Description | Waits for |
| --- | --- | --- |
| `human_task` | Creates a task inbox item for a user to complete | User completion |
| `automated_action` | Executes a system action (API call, data update, notification) | Action completion |
| `approval_gate` | Creates an approval chain and waits for decision | Approval decision |
| `notification` | Sends a notification to specified recipients | Delivery confirmation |
| `decision` | Evaluates conditions against workflow data and routes execution | Condition evaluation |
| `parallel` | Executes child steps concurrently and joins at completion | All branches complete |
| `loop` | Repeats a step sequence until exit condition is met | Exit condition |

### Dependency map entry

| Entry | Details |
| --- | --- |
| **Upstream dependencies** | the Intent Router agent intent routing; the Response Orchestration agent response orchestration; Notification service; Role directory lookup. |
| **Downstream dependencies** | Event bus consumers; audit trail storage; governance agents (e.g., the Lifecycle Governance agent); the Continuous Improvement agent; the Change Control agent; the Data Synchronisation agent. |
| **Data contracts** | Workflow definition schema (`ppm.workflow/v1`), approval request schema, decision schema, workflow instance schema, task inbox schema, and event payloads (workflow and approval lifecycle events). |
| **Infrastructure** | PostgreSQL or JSON file-backed state store; RabbitMQ or in-process task queue; Azure Monitor and Azure Event Grid for event integration; Azure Service Bus for event publishing. |

### Exposed APIs

| API | Description |
| --- | --- |
| `request_approval` | Submit a new approval request; creates an approval chain and returns `approval_id` |
| `apply_decision` | Record an approval decision (approve/reject) with actor and comments |
| `start_workflow` | Start a new workflow instance from a published definition |
| `get_workflow_status` | Get the current status of a workflow instance |
| `get_approval_status` | Get the current status of an approval request |
| `list_my_tasks` | List pending human tasks for a given user |
| `list_my_approvals` | List pending approval decisions for a given user |
| `pause_workflow` | Pause a running workflow instance |
| `resume_workflow` | Resume a paused workflow instance |
| `cancel_workflow` | Cancel a workflow instance and trigger compensation if configured |
| `retry_failed_task` | Retry a failed workflow step |
| `define_workflow` | Register a new workflow definition (YAML/JSON/BPMN) |
| `deploy_bpmn_workflow` | Import and deploy a workflow from BPMN 2.0 format |

### Events emitted

**Workflow events:**
- `workflow.instance.started` — New workflow instance created and execution begun
- `workflow.instance.completed` — Workflow instance reached terminal success state
- `workflow.instance.failed` — Workflow instance failed irrecoverably
- `workflow.instance.cancelled` — Workflow instance cancelled by user or system
- `workflow.instance.paused` / `workflow.instance.resumed`
- `workflow.step.started` / `workflow.step.completed` / `workflow.step.failed`
- `workflow.task.assigned` / `workflow.task.completed`

**Approval events:**
- `approval.created` — New approval request submitted
- `approval.assigned` — Approval assigned to approver(s)
- `approval.delegated` — Approval reassigned via delegation rule
- `approval.reminded` — Reminder sent to pending approver
- `approval.escalated` — SLA breach triggered escalation
- `approval.decision` — Decision recorded (approved/rejected)
- `approval.closed` — Approval chain completed

All events include `tenant_id`, `correlation_id`, `workflow_id` or `approval_id`, `timestamp`, and `actor` where applicable. Events are published to the Event Bus and written to the audit trail.

### Approvals as a workflow pattern

Approvals are **not** a separate subsystem — they are represented as a first-class workflow pattern using the `approval_gate` step type within the `ppm.workflow/v1` specification. This means every approval chain shares the same execution engine, state persistence, retry/compensation logic, audit trail, and monitoring infrastructure as any other workflow. An approval gate step defines:

```yaml
# ppm.workflow/v1
apiVersion: ppm.workflow/v1
kind: WorkflowDefinition
metadata:
  name: project-initiation
  version: "1.0"
spec:
  steps:
    - id: charter_review
      type: approval_gate
      config:
        request_type: charter_approval
        chain_type: sequential
        approvers:
          - role: project_sponsor
          - role: pmo_lead
        sla_hours: 48
        escalation_policy: risk_based
        notification_channels: [email, teams]
        deep_link_label: "View request"
      transitions:
        approved: requirements_phase
        rejected: revision_required

    - id: requirements_phase
      type: human_task
      config:
        assignee_role: business_analyst
        title: "Complete requirements document"
        deadline_hours: 120
      transitions:
        completed: design_review
```

## What's inside

- [src](/agents/core-orchestration/approval-workflow-agent/src): Implementation source for this component.
- [tests](/agents/core-orchestration/approval-workflow-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/core-orchestration/approval-workflow-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution. Other agents call this agent's APIs to request approvals, start workflows, query status, and manage human tasks.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name approval-workflow-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/core-orchestration/approval-workflow-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

Workflow definitions and templates are loaded from `ops/config/agents/approval-workflow-agent/` (durable workflow definitions and workflow templates).

### Dynamic escalation policy

Approval escalation timing is dynamically computed using risk and criticality context and loaded from `ops/config/agents/approval_policies.yaml`.

- `risk_thresholds`: maps computed request risk (`high`, `medium`, `low`) to escalation timeout hours.
- `criticality_levels`: maps computed criticality (`critical`, `high`, `normal`, `low`) to escalation timeout hours.

At runtime, the agent computes `risk_score` and `criticality_level` from request details (for example `amount`, `urgency`, `project_type`, and `strategic_importance`) and then picks the most conservative timeout across both mappings.

These values are persisted in approval metadata, included in audit events, and rendered in escalation notifications.

### Delegation rules

Approval delegation can be toggled and configured via `ops/config/agents/approval_workflow.yaml`.

- `delegation.enabled`: enables/disables delegate substitution during approver resolution.
- `delegation.default_duration_days`: default active window when a delegate rule omits an explicit end date.
- `delegation.rules`: map of approver IDs to one or more delegate rules. Each rule supports:
  - `delegate`: delegate user ID
  - `start`: ISO-8601 start datetime (optional)
  - `end`: ISO-8601 end datetime (optional)

Runtime behavior:

1. When approvers are resolved, the agent checks each approver for an active delegation rule at the current UTC time.
2. If a delegate is active, the delegate is assigned as the approver and delegation metadata is persisted in the approval record (`chain.delegations`).
3. Notification text includes: `You are receiving this approval request on behalf of {original_approver}` for delegated requests.
4. Notification subscription preferences now support `notify_delegate_directly` (default `true`):
   - `true`: deliver delegated notifications to the delegate user.
   - `false`: route delegated notifications to the original approver while preserving delegated assignment metadata.

### Notification localization and accessibility

Approval notifications now support locale-aware templates and accessibility-focused output controls.

- `notification_routing.*.locale`: Preferred notification locale (for example `en`, `fr`).
- `notification_routing.*.accessible_format`: Accessibility rendering mode. Supported values:
  - `text_only` (default): Plain text rendering.
  - `html_with_alt_text`: Sends a high-contrast HTML variant with larger default font sizing.
- Stored subscription preferences in `NotificationSubscriptionStore` now persist both `locale` and `accessible_format`.

Templates are loaded from locale folders under:

- `agents/core-orchestration/approval-workflow-agent/src/templates/{locale}/approval_notification.md`

If the configured locale template is missing, the agent falls back to English (`en`).

To add a new locale:

1. Create `src/templates/<new-locale>/approval_notification.md`.
2. Add all notification keys used by approval, escalation, and digest flows.
3. Validate with `pytest tests/notification/test_localization.py`.

### Integration services used

The approval-workflow-agent consumes the following shared integration services from `agents/common/connector_integration.py`:

| Service | Usage |
| --- | --- |
| **NotificationService** | Deliver approval notifications, reminders, and escalation alerts via email, Teams, Slack, and push channels. |
| **DatabaseStorageService** | Persist workflow definitions, workflow instance state, task inbox entries, and approval decision records. |
| **CalendarIntegrationService** (optional) | Schedule approval deadline reminders and review meetings in Outlook/Google Calendar. |

Workflow instance state is also backed by `workflow_state_store.py` (database-backed persistence) and `workflow_task_queue.py` (queue-driven task distribution) under `src/`.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
- Workflow definition validation fails: check the definition against `ppm.workflow/v1` schema; ensure all referenced step IDs exist and transition targets are valid.
- BPMN import fails: verify the BPMN XML is valid BPMN 2.0; check for unsupported element types in the import log.
