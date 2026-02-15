# Agent 10: Schedule Planning Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 10: Schedule Planning. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- [src](/agents/delivery-management/agent-10-schedule-planning/src): Implementation source for this component.
- [tests](/agents/delivery-management/agent-10-schedule-planning/tests): Test suites and fixtures.
- [Dockerfile](/agents/delivery-management/agent-10-schedule-planning/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-10-schedule-planning --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/agent-10-schedule-planning/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Scope, I/O contract, and decision responsibilities

### Intended scope (what Agent 10 owns)
- Convert WBS into a schedule, including task sequencing, dependencies, and milestone identification.
- Estimate task durations using AI/historical signals and apply them to schedules.
- Calculate CPM metrics (early/late dates, critical path, total duration).
- Produce schedule optimization, what-if analysis, and Monte Carlo risk simulations.
- Manage schedule baselines and variance tracking for timeline governance.
- Provide sprint planning artifacts (backlog/capacity views) when requested.

### Inputs, outputs, and required fields
The agent processes a single `action` per request. Required inputs are enforced at validation time.

| Action | Required Inputs | Outputs |
| --- | --- | --- |
| `create_schedule` | `project_id`, `wbs` | `schedule_id`, Gantt data, dependencies, critical path, milestones, duration |
| `estimate_duration` | `tasks` | Task durations + confidence intervals |
| `map_dependencies` | `schedule_id`, `dependencies` | Dependency network diagram |
| `calculate_critical_path` | `schedule_id` | Critical path tasks + total duration |
| `resource_constrained_schedule` | `schedule_id`, `resources` | Resource-leveled schedule + utilization + revised critical path |
| `run_monte_carlo` | `schedule_id`, `iterations` (optional) | Probabilistic completion dates + risk score/drivers |
| `track_milestones` | `schedule_id` | Milestone status + upcoming deadlines |
| `optimize_schedule` | `schedule_id` | Optimized schedule + improvement summary |
| `what_if_analysis` | `schedule_id`, `what_if_params` | Scenario comparison results |
| `manage_baseline` | `schedule_id` | Baseline ID + locked schedule metadata |
| `track_variance` | `schedule_id` | Variance analysis vs baseline |
| `sprint_planning` | `project_id`, `sprint_data` | Sprint backlog + capacity planning |
| `get_schedule` | `schedule_id` | Full schedule record |

### Decision responsibilities (what the agent decides)
- Task sequencing, dependency mapping suggestions, and CPM calculations.
- Duration estimates (including uncertainty) and milestone identification.
- Resource leveling logic when provided resource availability data.
- Schedule risk metrics derived from Monte Carlo simulation.
- Baseline lock decisions based on configured approval thresholds.

### Must / must-not behaviors
- **Must** reject requests that omit required `action` or required identifiers (`project_id`, `schedule_id`, `wbs`).
- **Must** treat resource availability as an input or external dependency (do not invent HR data).
- **Must** publish schedule updates and baseline events when integrations are enabled.
- **Must not** create or edit the enterprise risk register; only simulate schedule risk signals.
- **Must not** override resource allocations owned by Resource Capacity (Agent 11).
- **Must not** change governance policies managed by Lifecycle Governance (Agent 9) or Risk (Agent 15).

### Checkpoint
✅ **Planning I/O contract ready for execution.**

## Overlap analysis and handoff boundaries

### Agent 11 (Resource Capacity) overlap
- **Overlap area:** resource-constrained scheduling, utilization reporting, and allocation feasibility.
- **Handoff boundary:** Agent 10 consumes capacity/availability inputs from Agent 11 and returns schedule adjustments. Agent 11 remains the source of truth for allocations, calendars, and skill availability.
- **Escalation trigger:** when scheduling requires new/changed allocations, route to Agent 11 for approval or creation of allocations.

### Agent 15 (Risk/Issue Management) overlap
- **Overlap area:** schedule risk scoring and delay impacts.
- **Handoff boundary:** Agent 10 outputs schedule risk metrics and simulation results; Agent 15 owns risk register updates, mitigation plans, and issue escalation workflows.
- **Escalation trigger:** if schedule risk exceeds threshold or repeated delays are detected, notify Agent 15 with the risk signal.

## Gaps, inconsistencies, and alignment needs
- **Resource availability stub:** current availability intake is a pass-through. Align inputs from Agent 11 so `resources` includes capacity calendars and allocation constraints.
- **Event payload schema:** schedule risk/resource event payloads should be documented and shared with Agent 11/15 to avoid mismatch.
- **External sync toggles:** MS Project/Jira/Smartsheet sync is configured but requires connector mappings and UI indicators of sync status.
- **Prompt/tool alignment:** scheduling actions need prompt templates that enforce required fields and surface dependency types (FS/SS/FF/SF).
- **UI alignment:** surface critical path, baseline variance, and Monte Carlo percentiles in timeline UI cards.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.

## Risk-based planning integration
- Consumes `risk_data` (`project_risk_level`, `task_risks`) and applies duration buffers from `ops/config/agents/risk_adjustments.yaml`.
- Risk-adjusted durations are used during schedule creation and critical-path recalculation.
