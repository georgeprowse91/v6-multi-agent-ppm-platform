# Agent 11: Resource Capacity Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 11: Resource Capacity. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- [src](/agents/delivery-management/resource-management-agent/src): Implementation source for this component.
- [tests](/agents/delivery-management/resource-management-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/delivery-management/resource-management-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## Scope, inputs/outputs, and decisioning

### Intended scope
- Manage the resource pool (people/equipment), capacity calendars, and allocations.
- Intake resource demand, match skills, and route approvals.
- Forecast capacity vs. demand, plan capacity, and run scenarios.
- Sync capacity and profile data from HRIS, Planview, and Jira Tempo sources.

### Inputs (actions) and outputs
Supported `action` values in `process()` and their expected output shape:
- `add_resource`, `update_resource`, `delete_resource`: return resource profile and status.
- `request_resource`: return request ID, recommended candidates, approver, and approval payload.
- `approve_request`: return approval status and allocation if approved.
- `search_resources`: return matching resources and count.
- `match_skills`: return ranked candidates with match scores.
- `forecast_capacity`: return capacity/demand forecast, bottlenecks, and recommendations.
- `plan_capacity`: return capacity plan, gaps, and mitigation strategies.
- `scenario_analysis`: return baseline vs. scenario comparison with recommendation.
- `allocate_resource`: return allocation ID and allocation payload.
- `get_availability`: return calendar availability by day with average availability.
- `get_utilization`: return utilization summary and over/under allocations.
- `identify_conflicts`: return conflicts and resolution recommendations.
- `get_resource_pool`: return filtered resource pool.

### Decision responsibilities
- Determines if a resource request requires approval and routes it to approvers.
- Calculates candidate ranking and skill match thresholds for recommended resources.
- Validates allocations against allocation limits and overlap constraints.
- Detects over-allocation conflicts and produces mitigation recommendations.

### Must / must-not behaviors
**Must**
- Enforce allocation constraints when `enforce_allocation_constraints` is true.
- Reject allocations with invalid percentage or invalid date ordering.
- Persist resource/allocations to the state store and publish allocation events.
- Publish resource events for create/update/request/approval flows.

**Must not**
- Create allocations for unknown resources.
- Exceed maximum concurrent allocations or allocation thresholds when enforcement is enabled.
- Skip notification routing when approvals are required.

## Capacity allocation rules (execution-ready checkpoint)

Allocation validation must satisfy all of the following before persisting:
1. Resource exists in the pool (or synced store).
2. Allocation percentage is > 0 and ≤ 100.
3. Start date is on or before end date.
4. Overlapping allocations count is below `max_concurrent_allocations` when enforcement is enabled.
5. Total overlapping allocation percentage stays within `max_allocation_threshold` (expressed as a 1.0–1.0+ multiplier of 100%).

If any check fails, return a validation error and do not persist or publish allocation events.

## Overlap & handoff boundaries (Agents 10 & 12)

### Agent 10 (Schedule Planning)
**Overlap:** Resource-constrained scheduling, allocation feasibility, and calendar-aware planning.  
**Handoff boundary:** Agent 11 owns resource availability, allocation validation, and utilization. Agent 10 owns schedule creation, dependency mapping, critical path, and baseline management.  
**Integration expectation:** Agent 10 consumes allocation events (`resource.allocation.created`) and availability data (`get_availability`) rather than revalidating or mutating allocations.

### Agent 12 (Financial Management)
**Overlap:** Labor cost implications, forecast inputs, and resource cost rates.  
**Handoff boundary:** Agent 11 provides allocation/capacity facts and cost rates per resource; Agent 12 owns budgeting, cost tracking, and financial forecasting/variance analysis.  
**Integration expectation:** Agent 12 should treat Agent 11 as the system of record for allocations and resource availability, and request updates via `get_utilization`, `forecast_capacity`, or allocation events.

## Gaps, inconsistencies, and alignment requirements

### Functional gaps / inconsistencies
- **Approval routing details**: approval routing hints exist, but the requester/approver resolution lacks explicit mapping rules in this spec (rely on `approval_routing` config).  
- **Cost rate usage**: allocations include `cost_rate` at the resource level, but there is no explicit cost roll-up output in allocation responses.  
- **Conflict resolution outputs**: conflict recommendations are generated but not persisted or published as events.  

### Required alignment (prompt/tool/template/connector/UI)
- **Prompt & templates**: Ensure prompts include required fields for `request_resource` and `allocate_resource` actions (project_id, dates, effort, resource_id).  
- **Connectors**: Align Planview/Tempo connectors with allocation normalization fields (`allocation_id`, `resource_id`, `project_id`, dates, percentage).  
- **UI**: Resource allocation screens must surface validation errors, approval status, and conflicts; calendar view should consume `get_availability` responses.  
- **Event schema**: Downstream agents should subscribe to `resource.allocation.created` and `resource.request.approved/rejected` for schedule/financial sync.

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

### Resource & Capacity Agent Environment Variables

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

### Runtime Configuration Flags

- `max_concurrent_allocations`: Maximum number of overlapping allocations allowed per resource.
- `enforce_allocation_constraints`: Enable or disable conflict enforcement during allocation creation.

### New Dependencies

The agent uses these Python packages (already available in the repo requirements):
- `msal`
- `requests`
- `sqlalchemy`
- `redis`
- `azure-servicebus`

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.

## Risk-based capacity integration
- Applies risk load factors from `ops/config/agents/risk_adjustments.yaml` to demand and utilization calculations.
- Includes risk-driven recommendations in `plan_capacity` output when high/medium risk is present.
