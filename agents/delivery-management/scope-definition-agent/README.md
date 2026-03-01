# Project Definition Scope Specification

## Purpose

Define the responsibilities, workflows, and integration points for Project Definition Scope. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- [src](/agents/delivery-management/scope-definition-agent/src): Implementation source for this component.
- [tests](/agents/delivery-management/scope-definition-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/delivery-management/scope-definition-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name scope-definition-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/scope-definition-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

For optional external scope research, set `SEARCH_API_ENDPOINT` and `SEARCH_API_KEY`, and enable the agent flag `enable_external_research` in project configuration to allow outbound queries.

## Scope baseline (The Scope Definition agent)

### Intended scope

The Scope Definition agent owns project definition artifacts through the approved scope baseline. It is responsible for creating and maintaining:

- Project charter (business case, objectives, high-level constraints, success criteria).
- Scope statement (in/out of scope, deliverables).
- WBS structure derived from the scope statement.
- Requirements intake, traceability matrix, and stakeholder/RACI artifacts.
- Scope baseline creation and scope creep detection against the baseline.

### Inputs

- `charter_data` (title, description, project_type, methodology, objectives, in/out of scope, deliverables).
- `project_id` (for WBS, requirements, baseline, and scope creep checks).
- `scope_statement` (for WBS generation or baseline comparison).
- `requirements` (for requirements repository + traceability mapping).
- `stakeholders` (for register and RACI matrix).
- Optional `context` (tenant_id, correlation_id) and external research controls.

### Outputs

- Charter document + sectioned output.
- WBS hierarchy + ID.
- Requirements repository + traceability matrix.
- Stakeholder register + RACI matrix.
- Scope baseline snapshot + scope creep variance report.
- Scope research proposal (optional external research).

### Decision responsibilities

- Validate required fields per action before proceeding.
- Determine approval workflow triggers for scope changes or baseline deviations.
- Assess scope creep variance vs. configured threshold.
- Select data sources (templates, local context, external research) when generating scope proposals.

### Must / must-not behaviors

Must:
- Enforce required inputs for each action; reject incomplete requests.
- Emit baseline artifacts before schedule or resource planning proceeds.
- Record scope baseline snapshots in the scope baseline store.
- Publish scope baseline and scope change events for downstream agents.

Must not:
- Commit to schedule dates, durations, or resource assignments.
- Override approved baseline without an approval workflow decision.
- Create cost or financial commitments (owned by financial agent).

## Overlap & handoff boundaries (Agents 10–11)

### Overlap / leakage risks

- **The Schedule Planning agent (Schedule Planning):** WBS output can overlap with schedule work packages. the Scope Definition agent must stop at scope/WBS definition and avoid sequencing, durations, or dependency calculations.
- **The Resource Management agent (Resource Capacity):** RACI and stakeholder inputs can overlap with resource staffing. the Scope Definition agent must not assign named resources or capacity commitments.

### Handoff boundaries

- **To the Schedule Planning agent:** Provide WBS, scope baseline, and requirements traceability as inputs for activity definition, dependency mapping, and schedule development.
- **To the Resource Management agent:** Provide RACI roles, stakeholder register, and WBS deliverables as inputs for role-based capacity planning and allocation constraints.
- **From the Lifecycle Governance agent (Lifecycle Governance):** Receive approved baseline flags and governance gates before freezing scope.

## Functional gaps & alignment checklist

### Gaps / inconsistencies to resolve

- Scope baseline storage is in local tenant state; confirm downstream agents can read baseline summaries or require explicit event payloads.
- External scope research relies on `SEARCH_API_*` and optional LLM availability; ensure fallback logic is acceptable in offline environments.
- Traceability matrix formats may differ from downstream schedule/resource tooling; confirm required schema.

### Prompt/tool/template/connector/UI alignment

- **Prompting:** Ensure charter, scope statement, and WBS prompts align with organization templates (template library config).
- **Tools/Connectors:** Confirm document management, project management, and database services are configured to persist baseline artifacts.
- **UI:** Validate that scope baseline approvals and creep alerts surface in the orchestration UI for downstream agent gating.

## Dependency map entry (execution ready)

**Upstream dependencies**
- Project initiation context (sponsor, objectives, methodology).
- Governance approvals from the Lifecycle Governance agent for baseline freezing.

**Downstream dependencies**
- the Schedule Planning agent consumes WBS + baseline scope for schedule planning.
- the Resource Management agent consumes RACI roles + deliverables for capacity planning.

**Critical gating artifact**
- Scope baseline snapshot + approval status (must exist before schedule/resource planning).


### Baseline repository and traceability matrix

The Scope Definition agent now persists scope baselines in a SQL-backed repository (`services/scope_baseline`) using SQLAlchemy. By default it uses SQLite at `data/scope_baselines.db`, and can be overridden with `SCOPE_BASELINE_DB_URL`.

Key operations:

- `manage_scope_baseline`: locks and persists a baseline snapshot and returns `baseline_id`.
- `get_baseline`: retrieves a persisted baseline by `baseline_id`.
- `create_traceability_matrix`: generates requirement-to-WBS mappings with coverage status and emits matrix events.

Published events:

- `baseline.created` when a baseline record is persisted.
- `traceability.matrix.created` when a traceability matrix is generated.
- Existing `scope.baseline.locked` remains for baseline lock notifications.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
