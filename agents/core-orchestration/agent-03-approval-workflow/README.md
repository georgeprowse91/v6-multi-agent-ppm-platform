# Agent 03: Approval Workflow Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 03: Approval Workflow. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- [src](/agents/core-orchestration/agent-03-approval-workflow/src): Implementation source for this component.
- [tests](/agents/core-orchestration/agent-03-approval-workflow/tests): Test suites and fixtures.
- [Dockerfile](/agents/core-orchestration/agent-03-approval-workflow/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-03-approval-workflow --dry-run
```

Run unit tests (if present):

```bash
pytest agents/core-orchestration/agent-03-approval-workflow/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

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

- `agents/core-orchestration/agent-03-approval-workflow/src/templates/{locale}/approval_notification.md`

If the configured locale template is missing, the agent falls back to English (`en`).

To add a new locale:

1. Create `src/templates/<new-locale>/approval_notification.md`.
2. Add all notification keys used by approval, escalation, and digest flows.
3. Validate with `pytest tests/notification/test_localization.py`.

## Intended scope and responsibilities

**Agent 03 owns the approval workflow control loop.** It is responsible for:

- Validating approval requests and decision payloads.
- Resolving approvers (roles, delegation, escalation) and building approval chains.
- Emitting notifications, reminders, and audit events.
- Recording decisions and publishing approval lifecycle events.

**It must not:**

- Determine user intent or orchestrate multi-agent response composition (owned by Agents 01–02).
- Execute downstream governance state transitions (owned by governance agents such as Agent 09).
- Mutate project/system data outside the approval record, audit trail, and notification preferences.

## Inputs, outputs, and decision responsibilities

**Inputs (primary):**

- Approval request payloads with `request_type`, `request_id`, `requester`, `details`, and optional `context`.
- Approval decisions with `approval_id`, `decision`, `approver_id`, and optional `comments/context`.
- Notification preference actions (`subscribe`, `unsubscribe`, `update`, `interaction`).

**Outputs (primary):**

- Approval chain metadata (approvers, chain type, deadline, status).
- Notification dispatch attempts and escalation scheduling.
- Audit and analytics events for approvals and decisions.

**Decision responsibilities:**

- Approver routing and delegation resolution.
- Escalation timing and notification delivery strategy.
- Approval state transitions (`pending`, `approved`, `rejected`) as recorded in the approval store.

## Overlap boundaries and handoffs

**Agent 01 (Intent Router):**

- **Upstream handoff:** Agent 01 routes approval-intent requests here based on intent routing.
- **Boundary:** Agent 03 does not reclassify intent; it assumes intent is already validated.

**Agent 02 (Response Orchestration):**

- **Upstream handoff:** Agent 02 may request approval creation or decision recording when assembling responses.
- **Boundary:** Agent 03 does not craft user-facing narrative responses; it returns approval metadata/events for Agent 02 to present.

**Downstream governance agents (e.g., Agent 09 Lifecycle Governance):**

- **Downstream handoff:** Approval events (`approval.created`, `approval.decision`, `approval.approved/rejected`) are published for governance agents to act on.
- **Boundary:** Agent 03 does not execute lifecycle transitions or enforce governance gates beyond recording decisions and escalation.

## Functional gaps and alignment checkpoints

**Gaps / inconsistencies to track:**

- Approval gate definitions must be aligned with governance stage gates (Agent 09) and intent routing schema (Agent 01).
- Notification templates and escalation timing must align with UI and notification service capabilities.
- Event payload schemas must remain compatible with Event Bus and analytics consumers.

**Required alignment:** Prompting, tool schemas, and UI should use the same approval decision vocabulary (`pending`, `approved`, `rejected`) and include `approval_id`, `tenant_id`, and `correlation_id` where applicable.

## Checkpoint: approval gate definitions

| Gate | Trigger | Required inputs | Output |
| --- | --- | --- | --- |
| **Approval requested** | New approval request | `request_type`, `request_id`, `requester`, `details` | Approval chain + `approval_id`, status `pending` |
| **Decision recorded** | Approver submits decision | `approval_id`, `decision`, `approver_id`, optional `comments` | Stored decision + audit/event emission |
| **Escalation fired** | SLA timeout reached | Approval chain + escalation policy | Reminder notifications + escalation audit/event |
| **Approval closed** | Decision is `approved` or `rejected` | `approval_id`, decision | Finalized status + downstream governance events |

## Checkpoint: dependency map entry

| Entry | Details |
| --- | --- |
| **Upstream dependencies** | Agent 01 intent routing; Agent 02 response orchestration; Notification service; Role directory lookup. |
| **Downstream dependencies** | Event bus consumers; audit trail storage; governance agents (e.g., Agent 09 lifecycle governance). |
| **Data contracts** | Approval request schema, decision schema, and event payloads (approval lifecycle events). |

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
