# Agent 04: Demand Intake Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 04: Demand Intake. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Capture new demand requests from any intake channel and normalize into a single demand record.
- Validate minimum intake criteria (required fields and schema compliance).
- Categorize demand (project, change request, issue, idea) and flag likely duplicates.
- Provide a demand pipeline view for screening and routing.
- Notify the requester that intake is complete and the request is queued.

### Inputs
- `action`: `submit_request`, `check_duplicates`, `get_pipeline`.
- `request` payload (for submit/check): `title`, `description`, `business_objective` (required); `requester`, `business_unit`, `urgency`, `source` (optional).
- `filters` payload (for pipeline queries): `status`, `query`.
- `context`: `tenant_id`, `correlation_id` (optional; used for audit/event metadata).

### Outputs
- `submit_request`: `demand_id`, `category`, `status`, `duplicates_found`, `similar_requests`, `next_steps`.
- `check_duplicates`: `duplicates_found`, `similar_requests`.
- `get_pipeline`: `total_requests`, `by_status`, `by_category`, `items`.
- Event emission: `demand.created` with demand metadata for downstream agents.

### Decision responsibilities
- Accept/decline requests based on minimum intake criteria.
- Categorize and triage at intake only (no prioritization, funding, or scheduling).
- Flag duplicates but never auto-merge or auto-close demand.

### Must / must-not behaviors
- **Must** validate required fields and schema rules before accepting a demand.
- **Must** store the normalized demand record with created/tenant metadata.
- **Must** notify the requester and publish a `demand.created` event.
- **Must not** approve funding, assign budgets, or commit delivery resources.
- **Must not** set portfolio priority or sequencing (reserved for Agents 05–07).
- **Must not** bypass schema/rules validation even for internal requests.

## Overlap & handoff boundaries (Agents 05–07)

### Agent 05: Business Case Investment
- **Overlap risk**: early cost/benefit or ROI estimation during intake.
- **Boundary**: Demand Intake captures the request and triage metadata only. It hands off a validated demand record for Agent 05 to build the business case and investment recommendation.

### Agent 06: Portfolio Strategy Optimisation
- **Overlap risk**: intake-level prioritization, portfolio scoring, or portfolio fit analysis.
- **Boundary**: Demand Intake should provide categorization and urgency only; strategic scoring and optimization are performed by Agent 06 after a business case exists.

### Agent 07: Program Management
- **Overlap risk**: dependency mapping or program-level scheduling at intake.
- **Boundary**: Demand Intake does not define program structure. It delivers clean demand records for Agent 07 to manage dependencies once the demand is accepted into a program of work.

## Functional gaps / inconsistencies & alignment needs

- **Intake criteria gaps**: current schema does not capture scope size, estimated cost/benefit, regulatory impact, or dependency signals needed by downstream agents. Add optional fields or linked templates for these details.
- **Duplication logic**: duplicate detection is heuristic-only; add a manual review flag or human confirmation step to avoid false merges.
- **Triage routing**: no explicit routing rule set for which demands go to Agent 05 vs. Agent 07 (e.g., issues vs. initiatives). Add a routing table or decision matrix.
- **Prompt/template alignment**: ensure intake templates (forms, chat prompts, email ingestion) match required fields and the demand schema.
- **Connector alignment**: validate connectors for intake sources (email/forms/Slack/Teams) pass `tenant_id`, `requester`, and `source` consistently.
- **UI alignment**: intake UI should surface required fields, duplicate suggestions, and `next_steps` messaging.

## Checkpoint: intake criteria + dependency map entry

### Intake criteria (minimum)
- Required fields: `title`, `description`, `business_objective`.
- Accepted urgency values: `Low`, `Medium`, `High`, `Critical`.
- Validated against demand schema and rule set before persistence.

### Dependency map entry (ready for execution)
- **Upstream**: Intake channels (forms/email/chat), requester identity, tenant context.
- **Core services**: schema validator, rule engine, notification service, embedding + vector search index, tenant state store, event bus.
- **Downstream**: `demand.created` event → Agent 05 for business case; portfolio intake reporting → Agent 06; accepted program candidates → Agent 07.

## What's inside

- [agents/portfolio-management/agent-04-demand-intake/src](/agents/portfolio-management/agent-04-demand-intake/src): Implementation source for this component.
- [agents/portfolio-management/agent-04-demand-intake/tests](/agents/portfolio-management/agent-04-demand-intake/tests): Test suites and fixtures.
- [agents/portfolio-management/agent-04-demand-intake/Dockerfile](/agents/portfolio-management/agent-04-demand-intake/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-04-demand-intake --dry-run
```

Run unit tests (if present):

```bash
pytest agents/portfolio-management/agent-04-demand-intake/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
