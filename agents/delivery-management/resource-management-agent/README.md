# Resource Management Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Resource Management Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Manage the resource pool (people/equipment), capacity calendars, and allocations.
- Intake resource demand, match skills, and route approvals.
- Forecast capacity vs. demand, plan capacity, and run scenarios.
- Sync capacity and profile data from HRIS, Planview, and Jira Tempo sources.

### Inputs
- `action`: `add_resource`, `update_resource`, `delete_resource`, `request_resource`, `approve_request`, `search_resources`, `match_skills`, `forecast_capacity`, `plan_capacity`, `scenario_analysis`, `allocate_resource`, `get_availability`, `get_utilization`, `identify_conflicts`, `get_resource_pool`.
- Resource profiles, allocation payloads, skill requirements, capacity parameters.
- `context`: `tenant_id`, `correlation_id` (optional; used for audit/event metadata).

### Outputs
- `add_resource`/`update_resource`/`delete_resource`: resource profile and status.
- `request_resource`: request ID, recommended candidates, approver, and approval payload.
- `approve_request`: approval status and allocation if approved.
- `search_resources`: matching resources and count.
- `match_skills`: ranked candidates with match scores.
- `forecast_capacity`: capacity/demand forecast, bottlenecks, and recommendations.
- `plan_capacity`: capacity plan, gaps, and mitigation strategies.
- `scenario_analysis`: baseline vs. scenario comparison with recommendation.
- `allocate_resource`: allocation ID and allocation payload.
- `get_availability`: calendar availability by day with average availability.
- `get_utilization`: utilization summary and over/under allocations.
- `identify_conflicts`: conflicts and resolution recommendations.

### Decision responsibilities
- Determine if a resource request requires approval and route it to approvers.
- Calculate candidate ranking and skill match thresholds for recommended resources.
- Validate allocations against allocation limits and overlap constraints.
- Detect over-allocation conflicts and produce mitigation recommendations.

### Must / must-not behaviors
- **Must** enforce allocation constraints when `enforce_allocation_constraints` is true.
- **Must** reject allocations with invalid percentage or invalid date ordering.
- **Must** persist resource/allocations to the state store and publish allocation events.
- **Must** publish resource events for create/update/request/approval flows.
- **Must not** create allocations for unknown resources.
- **Must not** exceed maximum concurrent allocations or allocation thresholds when enforcement is enabled.
- **Must not** skip notification routing when approvals are required.

## Overlap & handoff boundaries

### Schedule Planning
- **Overlap risk**: resource-constrained scheduling, allocation feasibility, and calendar-aware planning.
- **Boundary**: The Resource Management agent owns resource availability, allocation validation, and utilization. The Schedule Planning agent owns schedule creation, dependency mapping, critical path, and baseline management. The Schedule Planning agent consumes allocation events (`resource.allocation.created`) and availability data (`get_availability`) rather than revalidating or mutating allocations.

### Financial Management
- **Overlap risk**: labor cost implications, forecast inputs, and resource cost rates.
- **Boundary**: The Resource Management agent provides allocation/capacity facts and cost rates per resource; the Financial Management agent owns budgeting, cost tracking, and financial forecasting/variance analysis. The Financial Management agent should treat the Resource Management agent as the system of record for allocations and resource availability.

## Functional gaps / inconsistencies & alignment needs

- **Approval routing details**: approval routing hints exist, but the requester/approver resolution lacks explicit mapping rules in this spec (rely on `approval_routing` config).
- **Cost rate usage**: allocations include `cost_rate` at the resource level, but there is no explicit cost roll-up output in allocation responses.
- **Conflict resolution outputs**: conflict recommendations are generated but not persisted or published as events.
- **Prompt & templates**: ensure prompts include required fields for `request_resource` and `allocate_resource` actions (project_id, dates, effort, resource_id).
- **Connectors**: align Planview/Tempo connectors with allocation normalization fields (`allocation_id`, `resource_id`, `project_id`, dates, percentage).
- **UI**: resource allocation screens must surface validation errors, approval status, and conflicts; calendar view should consume `get_availability` responses.
- **Event schema**: downstream agents should subscribe to `resource.allocation.created` and `resource.request.approved/rejected` for schedule/financial sync.

## Checkpoint: capacity allocation rules (execution-ready)

Allocation validation must satisfy all of the following before persisting:
1. Resource exists in the pool (or synced store).
2. Allocation percentage is > 0 and ≤ 100.
3. Start date is on or before end date.
4. Overlapping allocations count is below `max_concurrent_allocations` when enforcement is enabled.
5. Total overlapping allocation percentage stays within `max_allocation_threshold` (expressed as a 1.0–1.0+ multiplier of 100%).

If any check fails, return a validation error and do not persist or publish allocation events.

## What's inside

- [src](/agents/delivery-management/resource-management-agent/src): Implementation source for this component.
- [tests](/agents/delivery-management/resource-management-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/delivery-management/resource-management-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name resource-management-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/resource-management-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Resource & capacity agent environment variables

**Identity & Notifications (Microsoft Graph)**
- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`: Azure AD application credentials.

**Azure Cognitive Search & OpenAI Embeddings**
- `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`, `AZURE_SEARCH_INDEX`
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

**Azure ML Model Registry**
- `AZURE_ML_ENDPOINT`, `AZURE_ML_API_KEY`

**Azure AutoML Forecasting**
- `AZURE_AUTOML_ENDPOINT`, `AZURE_AUTOML_API_KEY`

**Azure Service Bus**
- `AZURE_SERVICEBUS_CONNECTION_STRING`, `AZURE_SERVICEBUS_QUEUE_NAME`

**Azure Communication Services**
- `AZURE_COMMUNICATION_SERVICE_CONNECTION_STRING`, `AZURE_COMMUNICATION_EMAIL_SENDER`

**HRIS Integrations**
- Workday: `WORKDAY_API_URL`, `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`, `WORKDAY_TOKEN_URL`
- SAP SuccessFactors: `SF_API_SERVER`, `SF_CLIENT_ID`, `SF_CLIENT_SECRET`, `SF_REFRESH_TOKEN`, `SF_TOKEN_URL`

**Capacity Sources**
- Planview: `PLANVIEW_INSTANCE_URL`, `PLANVIEW_CLIENT_ID`, `PLANVIEW_CLIENT_SECRET`, `PLANVIEW_REFRESH_TOKEN`, `PLANVIEW_CAPACITY_ENDPOINT`
- Jira Tempo: `JIRA_TEMPO_API_URL`, `JIRA_TEMPO_API_TOKEN`

**Storage & Caching**
- `RESOURCE_CAPACITY_DATABASE_URL` (PostgreSQL SQLAlchemy URL)
- `REDIS_URL`

### Runtime configuration flags

- `max_concurrent_allocations`: Maximum number of overlapping allocations allowed per resource.
- `enforce_allocation_constraints`: Enable or disable conflict enforcement during allocation creation.

### Risk-based capacity integration
- Applies risk load factors from `ops/config/agents/risk_adjustments.yaml` to demand and utilization calculations.
- Includes risk-driven recommendations in `plan_capacity` output when high/medium risk is present.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
