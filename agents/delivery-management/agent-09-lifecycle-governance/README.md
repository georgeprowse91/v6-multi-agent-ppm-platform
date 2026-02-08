# Agent 09: Lifecycle Governance Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 09: Lifecycle Governance. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Scope & Responsibilities

- Owns project lifecycle state, phase transitions, and governance gate enforcement.
- Monitors project health, publishes health events, and produces health dashboards/reports.
- Recommends and adapts delivery methodologies; maintains gate criteria and methodology maps.
- Records audit data for gate evaluations, overrides, and summaries.

## Inputs & Outputs

### Accepted actions (inputs)

- `initiate_project` (requires `project_data.project_id`, `name`, `methodology`).
- `transition_phase` (requires `project_id`, `target_phase`, plus orchestration metadata).
- `evaluate_gate`, `override_gate`, `get_gate_history`.
- `monitor_health`, `generate_health_report`, `get_health_dashboard`, `get_health_history`.
- `recommend_methodology`, `adjust_methodology`, `update_methodology_config`.
- `get_project_status`, `get_readiness_scores`, `train_readiness_model`, `score_readiness`.

### Primary outputs

- Lifecycle records (`current_phase`, `methodology_map`, `gates_passed`, readiness scores).
- Gate evaluation results (criteria status, readiness score, summaries, override audit).
- Health telemetry (composite score, metrics, status, recommendations).
- Events: `gate.passed`, `gate.failed`, `gate.overridden`, `phase.changed`, `project.transitioned`,
  `project.health.updated`, `project.health.report.generated`.

## Decision Responsibilities

- Enforce gate criteria before phase transitions; block transitions when criteria fail.
- Escalate gate override decisions to Agent 03 (Approval Workflow) and record approvals.
- Publish governance/health events for downstream analytics and UI consumption.

## Must / Must-Not Behaviors

**Must**

- Validate action inputs and required identifiers before processing.
- Persist gate evaluations, health metrics, and lifecycle state updates.
- Notify external systems and subscribers when gates pass/fail or health changes.

**Must-Not**

- Must not auto-override failed gates without an explicit approval workflow decision.
- Must not allow phase transitions when gate criteria are unmet (unless override approved).

## Overlaps & Handoff Boundaries

- **Agent 03 (Approval Workflow):** Agent 09 owns gate evaluation but must hand off any override
  request for approval; Agent 03 returns approval status and audit ID that Agent 09 records.
- **Agent 16 (Compliance Regulatory):** Agent 09 owns lifecycle gating but relies on Agent 16 to
  supply regulatory/compliance attestations that become gate criteria evidence (e.g., compliance
  sign-offs, audit readiness).

## Functional Gaps / Alignment Needs

- **Compliance monitoring gap:** Agent 09 declares compliance monitoring but currently has no
  explicit connector to Agent 16 for compliance evidence; define an event contract or API call.
- **Gate evidence ingestion:** Gate criteria depend on artifacts/approvals stored on the project
  record; UI/forms must capture these fields and sync them into the lifecycle store.
- **Prompt/template alignment:** Gate summaries and readiness scoring should use standardized
  checklist templates so that AI summaries and audits are consistent across phases.
- **Connector alignment:** External sync should map gate results into Planview/Clarity/Jira/Azure
  DevOps with consistent field names so dashboards reflect governance status.

## Governance Gate Definitions (Execution-Ready Defaults)

Default gates are derived from phase transitions and/or explicit gate requests. Criteria names
map directly to project artifacts/approvals and are evaluated during gate checks.

| Gate / Transition | Criteria (all required) | Evidence source |
| --- | --- | --- |
| `Initiate → Plan` (`initiate_to_plan_gate`) | `charter_document_complete`, `charter_approved`, `sponsor_assigned` | Charter artifact, approvals, sponsor assignment |
| `Plan → Execute` (`plan_to_execute_gate`) | `scope_baseline_approved`, `schedule_baseline_approved`, `budget_approved` | Scope/schedule/budget approvals |
| `Plan → Iterate` (`plan_to_iterate_gate`) | `scope_baseline_approved`, `schedule_baseline_approved`, `budget_approved` | Scope/schedule/budget approvals |
| `Execute → Monitor` / `Execute → Close` | `deliverables_complete`, `quality_criteria_met` | Deliverables artifact, quality metrics |
| `Monitor → Close` | `acceptance_complete` | Client acceptance approval |
| `Iterate → Release` | `iteration_complete`, `release_criteria_met` | Iteration artifacts, release readiness evidence |
| `Release → Close` | `release_criteria_met`, `closure_approved` | Release readiness, closure approval |
| `Sprint 0 → Sprint 1` | `sprint_planning_complete` | Sprint planning artifacts |
| `Sprint 1 → Sprint 2` | `sprint_review_complete`, `sprint_retrospective_complete` | Sprint review/retro artifacts |
| `Sprint 1 → Release` | `sprint_review_complete`, `sprint_retrospective_complete`, `release_criteria_met` | Sprint review/retro artifacts, release readiness |

Explicit gate requests (e.g., `charter_approved`, `baseline_approved`, `acceptance_complete`,
`closure_approved`, `release_criteria_met`) map to the same criteria list above.

## What's inside

- `agents/delivery-management/agent-09-lifecycle-governance/src`: Implementation source for this component.
- `agents/delivery-management/agent-09-lifecycle-governance/tests`: Test suites and fixtures.
- `agents/delivery-management/agent-09-lifecycle-governance/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution. Health monitoring now pulls metric values from domain agents via the shared metrics catalog and publishes `project.health.updated` / `project.health.report.generated` events for downstream analytics consumers.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-09-lifecycle-governance --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/agent-09-lifecycle-governance/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
