# Portfolio Optimisation Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Portfolio Optimisation Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Prioritize portfolio candidates using multi-criteria scoring (strategic alignment, ROI, risk, resource feasibility, compliance).
- Optimize portfolio composition against constraints (budget ceiling, resource capacity, risk appetite, minimum alignment).
- Run scenario analysis and compare outcomes across scenarios, including rebalancing recommendations.
- Emit portfolio prioritization events and audit records for traceability.

### Inputs
- `action` to select the workflow: prioritize, calculate alignment score, optimize, scenario analysis, rebalance, get status, compare scenarios, scenario CRUD, approval submission, or decision recording.
- `projects` list with costs, category, ROI, strategic objectives/tags, risk level, resource requirements, and compliance signals.
- `constraints` containing budget ceiling, resource capacity, risk appetite, minimum alignment score, and optional optimization method or weight overrides.
- `criteria_weights` (optional) to override default scoring weights for prioritization.
- `scenario`/`scenario_ids` for scenario CRUD and comparison workflows.

### Outputs
- Ranked portfolio records with per-criterion scores, recommendations, and audit metadata.
- Optimization results including selected projects, portfolio metrics, and trade-offs.
- Scenario comparison summaries and best-scenario recommendation when provided scenarios exist.
- Event payloads for downstream consumers (`portfolio.prioritized`).

### Decision responsibilities
- Assign approve/defer/reject recommendations based on weighted scores and policy guardrails.
- Select optimal portfolio compositions based on constraints and risk/return trade-offs.
- Recommend rebalancing actions to hit investment mix targets.

### Must / must-not behaviors
- **Must** validate `action` and required fields before processing.
- **Must** persist portfolio decisions with tenant and audit metadata.
- **Must** emit portfolio prioritization events for downstream agents.
- **Must not** approve a portfolio item that policy guardrails deny; downgrade approvals to defer when required.
- **Must not** run optimization without budget/resource constraints supplied (validation enforces this).
- **Must not** emit approval decisions without a `portfolio_id` (validation enforces required IDs).

## Overlap & handoff boundaries

### Business Case Investment
- **Overlap risk**: both agents touch ROI and investment sizing. The Portfolio Optimisation agent consumes project financials and produces portfolio recommendations; the Business Case agent owns the detailed business-case build and investment decision inputs.
- **Boundary**: The Business Case agent should provide validated project-level financials (cost, ROI, expected value, benefits) to the Portfolio Optimisation agent. The Portfolio Optimisation agent must not recalculate core business cases; it only uses those outputs for prioritization and optimization. This keeps case ownership with the Business Case agent and portfolio composition ownership with the Portfolio Optimisation agent.

### Program Management
- **Overlap risk**: program governance can overlap with portfolio rebalancing and scenario planning.
- **Boundary**: The Portfolio Optimisation agent outputs portfolio compositions, scenario outcomes, and rebalancing recommendations. The Program Management agent consumes the approved portfolio and coordinates execution sequencing, dependencies, and benefits realization. The Portfolio Optimisation agent must not own delivery scheduling or program dependency management beyond high-level resource capacity checks.

## Functional gaps / inconsistencies & alignment needs

- **Prompt alignment**: ensure upstream prompts consistently send `action`, `projects`, `constraints`, and `criteria_weights` as documented; otherwise validation will reject optimization workflows.
- **Tool/connector alignment**: financial enrichment depends on integration clients (`financial_agent`, resource agent) and optional database storage. Confirm connectors are wired and surfaced in orchestration templates/UI forms so required fields arrive populated.
- **Scenario UX alignment**: scenario CRUD exists in the agent; UI/templates should allow save/list/select scenario IDs to enable compare/what-if flows.
- **Policy guardrails**: the policy engine can override approvals; ensure downstream UI shows policy reasons and that orchestration keeps `correlation_id` for audit traceability.

## Checkpoint: strategy criteria + dependency map entry

### Strategy criteria (ready for execution)

- Strategic alignment (default weight 0.30)
- ROI (default weight 0.25)
- Risk (default weight 0.20)
- Resource feasibility (default weight 0.15)
- Compliance (default weight 0.10)

### Dependency map (ready for execution)

| Dependency | Source | Required By | Notes |
| --- | --- | --- | --- |
| Business-case financials (cost, ROI, expected value) | the Business Case agent | Prioritization/Optimization | Required for scoring and value calculations; the Portfolio Optimisation agent does not own business case creation. |
| Resource capacity & feasibility signals | Resource agent integration | Optimization/Rebalancing | Optional integration; falls back to project data if missing. |
| Portfolio approval decision | Approval agent integration | Submit/Record approval | Requires portfolio ID and decision payloads for audit trail continuity. |
| Event bus & audit trail | Runtime/event bus | Downstream orchestration | Required for portfolio.prioritized and policy audit events. |

## What's inside

- [src](/agents/portfolio-management/portfolio-optimisation-agent/src): Implementation source for this component.
- [tests](/agents/portfolio-management/portfolio-optimisation-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/portfolio-management/portfolio-optimisation-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name portfolio-optimisation-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/portfolio-management/portfolio-optimisation-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
