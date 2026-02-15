# Agent 06: Portfolio Strategy Optimisation Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 06: Portfolio Strategy Optimisation. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Scope validation (intended behaviors)

### Responsibilities (must)

- Prioritize portfolio candidates using multi-criteria scoring (strategic alignment, ROI, risk, resource feasibility, compliance).【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L20-L31】
- Optimize portfolio composition against constraints (budget ceiling, resource capacity, risk appetite, minimum alignment).【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L221-L280】
- Run scenario analysis and compare outcomes across scenarios, including rebalancing recommendations.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L151-L190】
- Emit portfolio prioritization events and audit records for traceability.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L1190-L1263】

### Inputs (expected)

- `action` to select the workflow: prioritize, calculate alignment score, optimize, scenario analysis, rebalance, get status, compare scenarios, scenario CRUD, approval submission, or decision recording.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L82-L144】
- `projects` list with costs, category, ROI, strategic objectives/tags, risk level, resource requirements, and compliance signals.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L193-L269】
- `constraints` containing budget ceiling, resource capacity, risk appetite, minimum alignment score, and optional optimization method or weight overrides.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L221-L246】
- `criteria_weights` (optional) to override default scoring weights for prioritization.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L42-L69】
- `scenario`/`scenario_ids` for scenario CRUD and comparison workflows.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L147-L189】

### Outputs (guaranteed)

- Ranked portfolio records with per-criterion scores, recommendations, and audit metadata.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L193-L346】
- Optimization results including selected projects, portfolio metrics, and trade-offs.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L279-L480】
- Scenario comparison summaries and best-scenario recommendation when provided scenarios exist.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L1104-L1156】
- Event payloads for downstream consumers (`portfolio.prioritized`).【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L1215-L1247】

### Decision responsibilities (agent-owned)

- Assign approve/defer/reject recommendations based on weighted scores and policy guardrails.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L239-L296】
- Select optimal portfolio compositions based on constraints and risk/return trade-offs.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L221-L480】
- Recommend rebalancing actions to hit investment mix targets.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L969-L1067】

### Must-not behaviors (explicit constraints)

- Must not approve a portfolio item that policy guardrails deny; downgrade approvals to defer when required.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L257-L286】
- Must not run optimization without budget/resource constraints supplied (validation enforces this).【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L101-L128】
- Must not emit approval decisions without a `portfolio_id` (validation enforces required IDs).【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L119-L128】

## Overlap & handoff boundaries

### Agent 05 (Business Case Investment)

**Overlap risk:** Both agents touch ROI and investment sizing. Agent 06 consumes project financials and produces portfolio recommendations; Agent 05 owns the detailed business-case build and investment decision inputs.

**Handoff boundary:** Agent 05 should provide validated project-level financials (cost, ROI, expected value, benefits) to Agent 06. Agent 06 must not recalculate core business cases; it only uses those outputs for prioritization and optimization. This keeps case ownership with Agent 05 and portfolio composition ownership with Agent 06.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L221-L369】

### Agent 07 (Program Management)

**Overlap risk:** Program governance can overlap with portfolio rebalancing and scenario planning.

**Handoff boundary:** Agent 06 outputs portfolio compositions, scenario outcomes, and rebalancing recommendations. Agent 07 consumes the approved portfolio and coordinates execution sequencing, dependencies, and benefits realization. Agent 06 must not own delivery scheduling or program dependency management beyond high-level resource capacity checks.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L279-L1067】

## Functional gaps & alignment needs

- **Prompt alignment:** Ensure upstream prompts consistently send `action`, `projects`, `constraints`, and `criteria_weights` as documented; otherwise validation will reject optimization workflows.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L82-L145】
- **Tool/connector alignment:** Financial enrichment depends on integration clients (`financial_agent`, resource agent) and optional database storage. Confirm connectors are wired and surfaced in orchestration templates/UI forms so required fields arrive populated.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L70-L92】
- **Scenario UX alignment:** Scenario CRUD exists in the agent; UI/templates should allow save/list/select scenario IDs to enable compare/what-if flows.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L147-L189】
- **Policy guardrails:** The policy engine can override approvals; ensure downstream UI shows policy reasons and that orchestration keeps `correlation_id` for audit traceability.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L1187-L1263】

## Checkpoint: strategy criteria + dependency map entry

### Strategy criteria (ready for execution)

- Strategic alignment (default weight 0.30)
- ROI (default weight 0.25)
- Risk (default weight 0.20)
- Resource feasibility (default weight 0.15)
- Compliance (default weight 0.10)【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L42-L69】

### Dependency map (ready for execution)

| Dependency | Source | Required By | Notes |
| --- | --- | --- | --- |
| Business-case financials (cost, ROI, expected value) | Agent 05 | Prioritization/Optimization | Required for scoring and value calculations; Agent 06 does not own business case creation.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L221-L369】 |
| Resource capacity & feasibility signals | Resource agent integration | Optimization/Rebalancing | Optional integration; falls back to project data if missing.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L746-L772】 |
| Portfolio approval decision | Approval agent integration | Submit/Record approval | Requires portfolio ID and decision payloads for audit trail continuity.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L119-L189】 |
| Event bus & audit trail | Runtime/event bus | Downstream orchestration | Required for portfolio.prioritized and policy audit events.【F:agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py†L1190-L1263】 |

## What's inside

- [src](/agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src): Implementation source for this component.
- [tests](/agents/portfolio-management/agent-06-portfolio-strategy-optimisation/tests): Test suites and fixtures.
- [Dockerfile](/agents/portfolio-management/agent-06-portfolio-strategy-optimisation/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-06-portfolio-strategy-optimisation --dry-run
```

Run unit tests (if present):

```bash
pytest agents/portfolio-management/agent-06-portfolio-strategy-optimisation/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
