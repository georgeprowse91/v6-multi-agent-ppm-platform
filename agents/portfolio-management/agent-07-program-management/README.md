# Agent 07: Program Management Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 07: Program Management. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Scope validation (intended behavior)

### Intended scope & responsibilities
- Owns program setup and coordination across multiple projects (create program, generate integrated roadmaps, track inter-project dependencies, aggregate benefits, coordinate shared resources, identify synergies, analyze change impact, monitor program health, optimize program schedules, and manage program-level approval/decision records).【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L25-L118】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L142-L310】
- Acts as the program-level orchestrator that pulls data from delivery agents (schedule, resource, financial, risk, quality, project definition, lifecycle) to compute cross-project insights, health, and optimization outcomes.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L92-L118】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L352-L904】
- Publishes program events (created, roadmap updated, health updated, optimized, decision recorded) and stores program artifacts in tenant state or databases for downstream consumption.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L331-L404】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L708-L820】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L2460-L2617】

### Inputs & outputs (contract-level expectations)
- **Inputs:** `action` plus supporting data per action (e.g., `program` for creation; `program_id` for roadmap, dependencies, health, optimization; `change` for impact analysis).【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L142-L309】
- **Program creation input:** `program.name`, `program.description`, `program.strategic_objectives`, `program.constituent_projects` (required). Optional `methodology`, `portfolio_id`, `created_by` metadata.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L173-L266】
- **Primary outputs:**
  - Program record with `program_id`, `status`, `constituent_projects`, and next steps.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L240-L309】
  - Integrated roadmap payload (milestones, dependencies, critical path, timelines).【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L312-L412】
  - Dependency graphs + analysis and optimization recommendations.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L413-L504】
  - Aggregated benefits/ROI, resource coordination, synergy opportunities, change impact assessment, health metrics, optimization output, and approval/decision records.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L506-L1172】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L2460-L3076】

### Decision responsibilities
- **Owns program-level coordination decisions** such as dependency sequencing recommendations, resource contention resolution guidance, synergy prioritization, and program optimization scoring.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L413-L1172】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L2460-L2930】
- **Delegates domain-specific decisions** (schedule health, budget health, risk health, quality health, resource health) to delivery agents; Program Management only aggregates and weights them into a composite score.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L708-L820】
- **Escalates approval decisions** to the Approval Workflow Agent when configured, then records the decision log and publishes program decision events.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L2982-L3076】

### Must / must-not behaviors
- **Must** validate `action` and `program_id`/required program fields before processing, and **must** fail fast on unknown actions or missing IDs.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L142-L223】
- **Must** persist program, roadmap, dependencies, health, optimization, and decision artifacts to tenant stores / database when configured.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L240-L412】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L676-L820】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L2571-L2617】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L3040-L3076】
- **Must not** redefine project-level scope, schedules, budgets, risks, or quality plans; those remain owned by delivery agents (08–16). Program Management only aggregates, correlates, and optimizes at program level.【F:agents/delivery-management/agent-08-project-definition-scope/src/project_definition_agent.py†L1-L83】【F:agents/delivery-management/agent-10-schedule-planning/src/schedule_planning_agent.py†L1-L63】【F:agents/delivery-management/agent-11-resource-capacity/src/resource_capacity_agent.py†L1-L60】【F:agents/delivery-management/agent-12-financial-management/src/financial_management_agent.py†L1-L59】【F:agents/delivery-management/agent-14-quality-management/src/quality_management_agent.py†L1-L56】【F:agents/delivery-management/agent-15-risk-issue-management/src/risk_management_agent.py†L1-L52】

## Overlap / leakage analysis

### Portfolio agents (04–06)
- **Agent 04 Demand Intake** handles intake and initial demand capture; Program Management should not accept demand intake directly beyond `create_program` for already-approved demand packages.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L240-L309】
- **Agent 05 Business Case Investment** owns project-level benefit/cost baselines; Program Management aggregates benefits from project business cases and must avoid duplicating business case creation logic.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L506-L603】
- **Agent 06 Portfolio Strategy Optimisation** optimizes across the portfolio; Program Management optimizes within a program. Ensure program optimization outputs roll up to portfolio-level optimization without altering portfolio-wide priorities.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L2460-L2617】

### Delivery agents (08–16)
- **Project Definition (08)** supplies charters and scope; Program Management consumes project detail for synergy analysis and must not alter scope baselines directly.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L896-L1005】【F:agents/delivery-management/agent-08-project-definition-scope/src/project_definition_agent.py†L1-L83】
- **Lifecycle Governance (09)** enforces phase gates/health; Program Management aggregates health and publishes program-level status without bypassing lifecycle gate controls.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L708-L820】【F:agents/delivery-management/agent-09-lifecycle-governance/src/project_lifecycle_agent.py†L1-L63】
- **Schedule Planning (10)** creates project schedules; Program Management references schedules to build program roadmaps, critical paths, and optimization scenarios.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L312-L493】【F:agents/delivery-management/agent-10-schedule-planning/src/schedule_planning_agent.py†L1-L63】
- **Resource Capacity (11)** owns resource allocation/utilization; Program Management identifies cross-project conflicts and recommends sequencing changes but should not override allocations directly.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L605-L703】【F:agents/delivery-management/agent-11-resource-capacity/src/resource_capacity_agent.py†L1-L60】
- **Financial Management (12)** owns budgets, forecasts, and ROI; Program Management aggregates benefits/costs and program-level ROI and must avoid maintaining separate project-level ledgers.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L506-L603】【F:agents/delivery-management/agent-12-financial-management/src/financial_management_agent.py†L1-L59】
- **Vendor & Procurement (13)** owns vendor onboarding/contracts; Program Management only flags program-level vendor synergies and consolidation opportunities, not procurement actions.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L774-L900】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1-L33】
- **Quality (14)** owns test/defect/audit; Program Management consumes quality health metrics for the composite score and should not create quality plans.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L708-L820】【F:agents/delivery-management/agent-14-quality-management/src/quality_management_agent.py†L1-L56】
- **Risk (15)** owns risk registers and mitigations; Program Management aggregates risk health and change impact but must not maintain a standalone risk register.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L708-L820】【F:agents/delivery-management/agent-15-risk-issue-management/src/risk_management_agent.py†L1-L52】
- **Compliance (16)** governs regulatory compliance; Program Management should include compliance outputs in program reporting but must not alter compliance control mappings or evidence directly.【F:agents/delivery-management/agent-16-compliance-regulatory/src/compliance_regulatory_agent.py†L1-L52】

## Functional gaps / inconsistencies to address
- **Input contract gaps:** no explicit schema enforcement for roadmap/benefit/health/optimization inputs (beyond `action` and `program_id`), which can cause inconsistent payloads between orchestration and UI/API layers.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L142-L309】
- **Program start/end calculation:** `_calculate_program_start` and `_calculate_program_end` currently return “now” rather than deriving from schedules, which can misalign program timeline reporting with schedule planning outputs.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L1063-L1074】
- **Dependency type consistency:** inter-project dependencies use program-specific types (`schedule_overlap`, `shared_resource`, `resource_contention`), while delivery schedule planning uses traditional FS/SS/FF/SF types; map or normalize when handing off to schedule agents or UI visualizations.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L934-L1037】【F:agents/delivery-management/agent-10-schedule-planning/src/schedule_planning_agent.py†L1-L63】
- **Approval boundary:** program approval exists, but no explicit linkage to lifecycle gates or compliance approvals; integrate approval outcomes with delivery governance to avoid conflicting approvals.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L2982-L3039】【F:agents/delivery-management/agent-09-lifecycle-governance/src/project_lifecycle_agent.py†L1-L63】

## Alignment requirements (prompt/tool/template/connector/UI)
- **Prompt/template alignment:** ensure program creation UI/API supplies `strategic_objectives` and `constituent_projects`, and downstream UI supports displaying program roadmaps, dependency graphs, health, and optimization artifacts as stored by the agent.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L173-L309】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L312-L412】
- **Connector alignment:** Planview/Clarity/Jira/Azure DevOps mappings and Cosmos dependency graphs are optional integrations; UI and orchestration should degrade gracefully when connectors are absent and fall back to stored tenant-state data.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L186-L204】【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L1730-L2069】
- **Tool alignment:** schedule, resource, financial, risk, quality agents must expose the actions used here (`get_schedule`, `get_utilization`, `get_financial_summary`, health actions) to keep program health calculations consistent.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L844-L1187】

## Program → Delivery handoff definition (ready for execution)

### Handoff package (from Program Management to Delivery orchestration)
Provide a program handoff payload containing:
- `program_id`, `portfolio_id`, `name`, `description`, `methodology`, `strategic_objectives` (from program record).【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L240-L266】
- `constituent_projects` with each project’s charter/scope references (from Project Definition Agent) and schedule/budget baselines if available.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L896-L1005】【F:agents/delivery-management/agent-08-project-definition-scope/src/project_definition_agent.py†L1-L83】
- `roadmap` (milestones, dependencies, critical path) for scheduling coordination and dependency visualization.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L312-L412】
- `resource_conflicts` and `resource_allocation_recommendations` to seed Resource Capacity mitigation workflows.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L605-L703】
- `benefit_aggregation` and `program_roi` for Financial Management tracking and variance monitoring.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L506-L603】
- `health_snapshot` (composite score + domain metrics) to inform Lifecycle Governance and delivery dashboards.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L708-L820】

### Delivery-side obligations
- Delivery agents must treat program-level dependencies and roadmap as constraints, not replacements for project-level scheduling and scope baselines.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L312-L504】【F:agents/delivery-management/agent-10-schedule-planning/src/schedule_planning_agent.py†L1-L63】
- Delivery governance must acknowledge program approval outcomes and capture any gate deviations as program-level change impacts for feedback to Program Management.【F:agents/portfolio-management/agent-07-program-management/src/program_management_agent.py†L2982-L3076】【F:agents/delivery-management/agent-09-lifecycle-governance/src/project_lifecycle_agent.py†L1-L63】

## What's inside

- [src](/agents/portfolio-management/agent-07-program-management/src): Implementation source for this component.
- [tests](/agents/portfolio-management/agent-07-program-management/tests): Test suites and fixtures.
- [Dockerfile](/agents/portfolio-management/agent-07-program-management/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-07-program-management --dry-run
```

Run unit tests (if present):

```bash
pytest agents/portfolio-management/agent-07-program-management/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
