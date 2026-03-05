# Program Management Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Program Management Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Own program setup and coordination across multiple projects (create program, generate integrated roadmaps, track inter-project dependencies, aggregate benefits, coordinate shared resources, identify synergies, analyze change impact, monitor program health, optimize program schedules, and manage program-level approval/decision records).
- Act as the program-level orchestrator that pulls data from delivery agents (schedule, resource, financial, risk, quality, project definition, lifecycle) to compute cross-project insights, health, and optimization outcomes.
- Publish program events (created, roadmap updated, health updated, optimized, decision recorded) and store program artifacts in tenant state or databases for downstream consumption.

### Inputs
- `action` plus supporting data per action (e.g., `program` for creation; `program_id` for roadmap, dependencies, health, optimization; `change` for impact analysis).
- Program creation input: `program.name`, `program.description`, `program.strategic_objectives`, `program.constituent_projects` (required). Optional `methodology`, `portfolio_id`, `created_by` metadata.

### Outputs
- Program record with `program_id`, `status`, `constituent_projects`, and next steps.
- Integrated roadmap payload (milestones, dependencies, critical path, timelines).
- Dependency graphs + analysis and optimization recommendations.
- Aggregated benefits/ROI, resource coordination, synergy opportunities, change impact assessment, health metrics, optimization output, and approval/decision records.

### Decision responsibilities
- Own program-level coordination decisions such as dependency sequencing recommendations, resource contention resolution guidance, synergy prioritization, and program optimization scoring.
- Delegate domain-specific decisions (schedule health, budget health, risk health, quality health, resource health) to delivery agents; Program Management only aggregates and weights them into a composite score.
- Escalate approval decisions to the Approval Workflow Agent when configured, then record the decision log and publish program decision events.

### Must / must-not behaviors
- **Must** validate `action` and `program_id`/required program fields before processing, and fail fast on unknown actions or missing IDs.
- **Must** persist program, roadmap, dependencies, health, optimization, and decision artifacts to tenant stores / database when configured.
- **Must not** redefine project-level scope, schedules, budgets, risks, or quality plans; those remain owned by delivery agents. Program Management only aggregates, correlates, and optimizes at program level.

## Overlap & handoff boundaries

### Demand Intake
- **Overlap risk**: Program Management should not accept demand intake directly beyond `create_program` for already-approved demand packages.
- **Boundary**: The Demand Intake agent handles intake and initial demand capture.

### Business Case Investment
- **Overlap risk**: the Business Case agent owns project-level benefit/cost baselines; Program Management aggregates benefits from project business cases.
- **Boundary**: Program Management must avoid duplicating business case creation logic.

### Portfolio Strategy Optimisation
- **Overlap risk**: the Portfolio Optimisation agent optimizes across the portfolio; Program Management optimizes within a program.
- **Boundary**: Ensure program optimization outputs roll up to portfolio-level optimization without altering portfolio-wide priorities.

### Delivery agents (08–16)
- **Project Definition (08)**: supplies charters and scope; Program Management consumes project detail for synergy analysis and must not alter scope baselines directly.
- **Lifecycle Governance (09)**: enforces phase gates/health; Program Management aggregates health and publishes program-level status without bypassing lifecycle gate controls.
- **Schedule Planning (10)**: creates project schedules; Program Management references schedules to build program roadmaps, critical paths, and optimization scenarios.
- **Resource Capacity (11)**: owns resource allocation/utilization; Program Management identifies cross-project conflicts and recommends sequencing changes but should not override allocations directly.
- **Financial Management (12)**: owns budgets, forecasts, and ROI; Program Management aggregates benefits/costs and program-level ROI and must avoid maintaining separate project-level ledgers.
- **Vendor & Procurement (13)**: owns vendor onboarding/contracts; Program Management only flags program-level vendor synergies and consolidation opportunities, not procurement actions.
- **Quality (14)**: owns test/defect/audit; Program Management consumes quality health metrics for the composite score and should not create quality plans.
- **Risk (15)**: owns risk registers and mitigations; Program Management aggregates risk health and change impact but must not maintain a standalone risk register.
- **Compliance (16)**: governs regulatory compliance; Program Management should include compliance outputs in program reporting but must not alter compliance control mappings or evidence directly.

## Functional gaps / inconsistencies & alignment needs

- **Input contract gaps**: no explicit schema enforcement for roadmap/benefit/health/optimization inputs (beyond `action` and `program_id`), which can cause inconsistent payloads between orchestration and UI/API layers.
- **Program start/end calculation**: `_calculate_program_start` and `_calculate_program_end` currently return "now" rather than deriving from schedules, which can misalign program timeline reporting with schedule planning outputs.
- **Dependency type consistency**: inter-project dependencies use program-specific types (`schedule_overlap`, `shared_resource`, `resource_contention`), while delivery schedule planning uses traditional FS/SS/FF/SF types; map or normalize when handing off to schedule agents or UI visualizations.
- **Approval boundary**: program approval exists, but no explicit linkage to lifecycle gates or compliance approvals; integrate approval outcomes with delivery governance to avoid conflicting approvals.
- **Prompt/template alignment**: ensure program creation UI/API supplies `strategic_objectives` and `constituent_projects`, and downstream UI supports displaying program roadmaps, dependency graphs, health, and optimization artifacts as stored by the agent.
- **Connector alignment**: Planview/Clarity/Jira/Azure DevOps mappings and Cosmos dependency graphs are optional integrations; UI and orchestration should degrade gracefully when connectors are absent and fall back to stored tenant-state data.
- **Tool alignment**: schedule, resource, financial, risk, quality agents must expose the actions used here (`get_schedule`, `get_utilization`, `get_financial_summary`, health actions) to keep program health calculations consistent.

## Checkpoint: program → delivery handoff definition (ready for execution)

### Handoff package (from Program Management to Delivery orchestration)
Provide a program handoff payload containing:
- `program_id`, `portfolio_id`, `name`, `description`, `methodology`, `strategic_objectives` (from program record).
- `constituent_projects` with each project's charter/scope references (from Project Definition Agent) and schedule/budget baselines if available.
- `roadmap` (milestones, dependencies, critical path) for scheduling coordination and dependency visualization.
- `resource_conflicts` and `resource_allocation_recommendations` to seed Resource Capacity mitigation workflows.
- `benefit_aggregation` and `program_roi` for Financial Management tracking and variance monitoring.
- `health_snapshot` (composite score + domain metrics) to inform Lifecycle Governance and delivery dashboards.

### Delivery-side obligations
- Delivery agents must treat program-level dependencies and roadmap as constraints, not replacements for project-level scheduling and scope baselines.
- Delivery governance must acknowledge program approval outcomes and capture any gate deviations as program-level change impacts for feedback to Program Management.

## What's inside

- [src](/agents/portfolio-management/program-management-agent/src): Implementation source for this component.
- [tests](/agents/portfolio-management/program-management-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/portfolio-management/program-management-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name program-management-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/portfolio-management/program-management-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
