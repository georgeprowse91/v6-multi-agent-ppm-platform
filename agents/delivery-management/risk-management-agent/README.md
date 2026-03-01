# Agent 15: Risk Issue Management Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 15: Risk Issue Management. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Scope, intent, and decision rights

### Intended scope
- Owns the end-to-end risk/issue lifecycle: identification, assessment, scoring, prioritization, mitigation planning, and ongoing monitoring across projects, programs, and portfolios.
- Maintains a central risk register with scoring, triggers, mitigation plans, and event history.
- Produces quantitative outputs (Monte Carlo, sensitivity analysis) and qualitative guidance (mitigation strategies).
- Publishes risk events for downstream agents and dashboards.

### Inputs
- Project/portfolio context: project_id, portfolio_id, owners, classifications.
- Operational signals: schedule delays, cost overruns, quality defect rates, resource utilization.
- PM connector signals (Planview/MS Project/Jira/Azure DevOps) tagged as risks.
- Documents and knowledge base content (SharePoint/Confluence) for risk extraction and mitigations.
- Optional ML services or cognitive search results for risk extraction and scoring.

### Outputs
- Risk register records with probability/impact scoring and status updates.
- Mitigation plans and trigger definitions.
- Risk datasets stored in data lake/synapse and optional GRC integration objects.
- Event bus messages (e.g., `risk.triggered`, `risk.created`, `risk.updated`) to drive escalation and governance.
- Reports: summary, detailed, mitigation status.

### Decision responsibilities
- Determine risk classification, scoring, and priority ordering.
- Decide when a signal crosses a trigger threshold and must escalate.
- Recommend mitigation strategies; do not approve or execute them.
- Escalate high-severity risks to governance and compliance agents and flag owners.

### Must / must-not behaviors
- Must validate risk records against schema and data-quality rules before publishing.
- Must capture source/provenance for extracted risks (connector, doc, model).
- Must emit event updates when risk status, scoring, or triggers change materially.
- Must not change project scope, schedule baselines, or financial forecasts directly (handoff to Agents 09/10/12).
- Must not triage or close defects directly (handoff to Agent 14).
- Must not approve compliance exceptions (handoff to Agent 16).

## Overlap and handoff boundaries

### Agent 14: Quality Management
- Overlap: quality defects, test failures, and quality KPIs are risk signals.
- Handoff boundary: Agent 14 owns defect triage and quality remediation. Agent 15 only interprets those signals to update risk scores, create risk entries, and trigger escalation when thresholds are exceeded.
- Required interface: structured quality signals (defect rate, severity, trend) and QA milestone outcomes.

### Agent 09: Lifecycle Governance
- Overlap: project health and governance escalations depend on risk status.
- Handoff boundary: Agent 09 owns phase-gate decisions and portfolio health reporting. Agent 15 supplies risk status, trigger events, and mitigation readiness for inclusion in governance scorecards.
- Required interface: governance receives `risk.triggered`/`risk.updated` events and risk summaries per project/portfolio.

## Gaps, inconsistencies, and alignment needs

- Escalation taxonomy: ensure event names and severity labels are consistent with the governance event catalog so Agent 09 can consume them without translation.
- Issue vs. risk distinction: clarify in UI/templates when an item is a realized issue versus a potential risk; current implementation emphasizes risks and may need explicit “issue” status mapping.
- Connector alignment: PM connectors use heterogeneous fields (priority/severity/labels). Normalize into a shared risk signal schema for UI and reporting consistency.
- Mitigation ownership: mitigation plans are stored but require explicit ownership/approval workflow; align with governance templates for accountability and follow-through.

## Risk/issue escalation map (checkpoint)

| Trigger type | Threshold signal | Risk action | Escalation event | Governance handoff |
| --- | --- | --- | --- | --- |
| Cost overrun | overrun_pct ≥ threshold | increase score, update status | `risk.triggered` | Agent 09 updates health/phase gating |
| Schedule delay | delay_days ≥ threshold | increase score, update status | `risk.triggered` | Agent 09 updates health/phase gating |
| Quality defect rate | defect_rate ≥ threshold | increase score, update status | `risk.triggered` | Agent 14 notified; Agent 09 consumes summary |
| Resource utilization | utilization ≥ threshold | increase score, update status | `risk.triggered` | Agent 11 notified; Agent 09 consumes summary |
| High risk score | score ≥ high_risk_threshold | flag as high severity | `risk.updated` | Governance escalation workflow |

## What's inside

- [src](/agents/delivery-management/risk-management-agent/src): Implementation source for this component.
- [tests](/agents/delivery-management/risk-management-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/delivery-management/risk-management-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name risk-management-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/risk-management-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Risk data integrations

The risk management agent can connect to Azure services and project management platforms for enhanced analytics:

- **Cosmos DB / Azure SQL**: `COSMOS_DB_CONNECTION_STRING`, `COSMOS_DB_DATABASE`, or `AZURE_SQL_CONNECTION_STRING`
- **Azure Data Lake**: `AZURE_DATA_LAKE_FILE_SYSTEM`
- **Azure Synapse**: `AZURE_SYNAPSE_WORKSPACE`, `AZURE_SYNAPSE_SQL_POOL`, `AZURE_SYNAPSE_SPARK_POOL`
- **Azure ML**: `AZURE_ML_ENDPOINT`, `AZURE_ML_API_KEY`
- **Azure Cognitive Search**: `AZURE_COG_SEARCH_ENDPOINT`, `AZURE_COG_SEARCH_API_KEY`, `AZURE_COG_SEARCH_INDEX`
- **Service Bus events**: `AZURE_SERVICE_BUS_CONNECTION_STRING`, `EVENT_BUS_TOPIC`, `EVENT_BUS_SUBSCRIPTION`
- **PM connectors**: `PLANVIEW_INSTANCE_URL`, `MS_PROJECT_SITE_URL`, `JIRA_INSTANCE_URL`, `AZURE_DEVOPS_ORG_URL`
- **Knowledge bases**: `SHAREPOINT_SITE_URL`, `CONFLUENCE_URL`

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.

## Risk data outputs for downstream planning
- Risk prioritization and matrix outputs now include `risk_level` and optional `task_id`/`project_id` fields.
- Dashboard responses include a `risk_data` payload for schedule and resource agents.
