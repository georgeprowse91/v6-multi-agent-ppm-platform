# Agent 12: Financial Management Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 12: Financial Management. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- [src](/agents/delivery-management/financial-management-agent/src): Implementation source for this component.
- [tests](/agents/delivery-management/financial-management-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/delivery-management/financial-management-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name financial-management-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/financial-management-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

Additional configuration options supported by the Financial Management Agent:

- `exchange_rate_fixture`, `exchange_rate_api_url`: currency exchange sources.
- `tax_rate_fixture`, `tax_rate_api_url`: tax rate lookup configuration.
- `erp_pipelines`: list of Azure Data Factory pipelines to run for ERP ingestion.
- `service_bus`: `{ "connection_string": "...", "topic_name": "ppm-events" }` for financial event publishing.
- `key_vault`: `{ "vault_url": "...", "secrets": { "service_bus.connection_string": "secret-name" } }` to resolve credentials.
- `related_agent_endpoints`: `{ "resource_plan": "http://...", "schedule_progress": "http://...", "benefits": "http://..." }`.
- `related_agent_fixtures`: inline fixtures for local development and tests.

## Intended scope

Agent 12 owns financial execution for in-flight portfolios, programs, and projects. It focuses on budget baselines, cost tracking, forecasts, variance analysis, earned value, and profitability reporting. The agent integrates with ERP systems to reconcile funding and actuals, and publishes finance events to the service bus for downstream consumers. It also supports multi-currency conversions and tax handling where required by the portfolio. Source of truth for business-case creation and procurement decisions stays with other agents (see handoffs below).

## Inputs & outputs

**Primary inputs**

- `action`: Financial workflow selector (budget creation/update, cost tracking, forecast, variance, EVM, summary/reporting, currency conversion, profitability).  
- `budget`: Budget payload with project/portfolio identifiers, totals, and cost breakdowns.
- `costs`: Cost/transaction payloads for tracking actuals and accruals.
- `project_id` / `portfolio_id`: Entity identifiers for finance queries.
- `time_period`: Reporting range for forecast/variance.
- `context`: `tenant_id`, `correlation_id`, `actor_id` for auditability.

**Primary outputs**

- Budget baseline and approval status.
- Cost tracking summaries, accruals, and category breakdowns.
- Forecast projections and estimate-at-completion values.
- Variance and earned value metrics.
- Financial summaries and standardized reports (summary, variance, forecast, cash flow, profitability).
- Currency conversion results and profitability metrics (ROI/NPV/IRR/payback period).

## Decision responsibilities

- Validate budget integrity and data quality before persistence.
- Determine variance thresholds and flagging based on configured percent/absolute limits.
- Trigger approval workflows for budget baselines and updates.
- Reconcile funding availability with ERP transactions before confirming budget readiness.
- Publish finance events and audit logs for lifecycle visibility.

## Must / must-not behaviors

**Must**

- Enforce tenant scoping, correlation IDs, and actor attribution for auditability.
- Persist budgets, actuals, and forecasts to tenant stores and database storage.
- Emit audit events and publish finance lifecycle events for downstream analytics.
- Validate cost breakdowns and perform data quality checks before approvals.
- Resolve secrets via Key Vault configuration when provided.
- Call ERP integration for funding validation and cost transactions ingestion.

**Must not**

- Replace the Business Case & Investment agent for initial ROI/business case creation.
- Approve or reject procurement contracts (handoff to Vendor & Procurement agent).
- Bypass approval workflows when approval integration is enabled.
- Modify vendor records or procurement policies.

## Handoffs and overlap boundaries

**Agent 05 – Business Case & Investment**

Overlap risk: profitability and ROI metrics are calculated here for live performance, while Agent 05 owns initial business case creation and investment recommendations.  
**Handoff boundary:** Agent 12 consumes approved business case cash flow inputs (via agent integration or related agent endpoint) and tracks actuals/variance against the approved baseline. Agent 05 remains the source of truth for business-case narratives, scenario modeling, and investment decisions.

**Agent 13 – Vendor & Procurement**

Overlap risk: vendor invoices, contracts, and purchase orders influence actual costs.  
**Handoff boundary:** Agent 13 owns vendor onboarding, contract management, invoice capture, and procurement approvals. Agent 12 consumes invoice/actuals data (ERP/AP connectors or events) to update cost tracking and forecasts, and provides budget availability checks back to Agent 13.

## Functional gaps and alignment requirements

- **Prompt alignment:** Ensure orchestrator prompts pass `context` (tenant/correlation/actor IDs) and include `budget`/`costs` payloads with currency and cost breakdowns for approval readiness.
- **Tool alignment:** ERP connector and Service Bus event publishing are mandatory for production workflows; ensure connector registry and secrets are configured before live execution.
- **Template alignment:** Use the finance templates (cost management plan, cost baseline, variance report, financial risk plan) when generating reports or delivering documentation.
- **Connector alignment:** Confirm exchange-rate/tax-rate provider configs or fixture paths are available for multi-currency and tax handling.
- **UI alignment:** Financial dashboards should surface budget status (draft/approved), variance alerts, forecast accuracy, and approval trail links to the audit log.

## Execution checkpoints

- **Financial controls ready:** approval workflow integration, audit events, variance thresholds, and ERP funding validation enabled.
- **Dependency map entry ready:** Agent 12 depends on ERP finance connectors, approval workflow, service bus eventing, key vault secrets, and related agent endpoints for resource plans, schedule progress, and benefits.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
