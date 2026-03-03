# Analytics Insights Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Analytics Insights Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Scope, inputs, and outputs

**Intended scope**

- Portfolio-level analytics, dashboards, reporting, and narrative insights for project health, KPI tracking, and scenario analysis.
- Cross-domain event ingestion (schedule, deployment, risk, quality, resource) and KPI computation based on event history.
- Azure-first analytics stack orchestration (Synapse, Data Lake, Data Factory), plus Power BI embedding and narrative generation.

**Primary inputs**

- `action`: the requested operation. Supported values include: `aggregate_data`, `create_dashboard`, `generate_report`, `run_prediction`, `scenario_analysis`, `generate_narrative`, `track_kpi`, `query_data`, `natural_language_query`, `get_dashboard`, `get_insights`, `update_data_lineage`, `get_powerbi_report`, `orchestrate_etl`, `monitor_etl`, `train_kpi_model`, `provision_analytics_stack`, `ingest_sources`, `ingest_realtime_event`, `compute_kpis_batch`, `generate_periodic_report`.
- `tenant_id` (top-level or in `context`): required to scope storage and event history.
- Action-specific payloads:
  - `data_sources`, `dashboard`, `report`, `model_type`, `scenario`, `kpi`, `query`, `filters`, `dashboard_id`, `lineage`, `pipelines`, `run_id`, `report_type`, `user_context`, `event`, `event_type`, `training_payload`.

**Primary outputs**

- `aggregate_data`: record count, statistics, lineage ID, data lake paths, Synapse ingest metadata.
- `create_dashboard`: dashboard ID, widget count, refresh schedule, URL.
- `generate_report`: report ID, visualization count, narrative, download URL.
- `run_prediction`: prediction ID, predicted value, confidence + interval, recommendations.
- `scenario_analysis`: baseline, scenario metrics, comparison, recommendations + simulation summary.
- `generate_narrative`: narrative content with stored ID.
- `track_kpi`: KPI value, trend, threshold status + alert IDs.
- `query_data`/`natural_language_query`: query response payloads and timestamps.
- `get_insights`: anomalies/patterns + recommendations (also emits event bus updates).
- `generate_periodic_report`: periodic cross-project summary with cycle time, risk frequency, budget variance, trends, anomalies, and recommended process changes.
- `get_powerbi_report`: embed URL + access token.
- `provision_analytics_stack`/`ingest_sources`/`orchestrate_etl`/`monitor_etl`: operational pipeline metadata.

## Decision responsibilities

- Decide which KPI definitions to compute from incoming events and when to publish `analytics.kpi.updated`.
- Decide alerting outcomes for KPI thresholds and emit `analytics.kpi.threshold_breached`.
- Decide narrative wording and insight recommendations based on detected anomalies/patterns.
- Decide orchestration actions for data pipelines and provisioning.

## Must / must-not behaviors

**Must**

- Always validate `action` and required fields before executing.
- Always scope storage and event history operations by `tenant_id`.
- Always redact sensitive fields (PII) or mask lineage when `LINEAGE_MASK_SALT` is set.
- Publish analytics events (`analytics.insights.generated`, `analytics.kpi.updated`, etc.) when outcomes are produced.

**Must-not**

- Must not generate dashboards with more than the configured widget limit.
- Must not expose raw sensitive fields in lineage or event payloads.
- Must not run ML prediction without `model_type` and required inputs.

## Overlap, leakage, and handoff boundaries

**Coordination with the System Health agent (System Health Monitoring)**

- the Analytics Insights agent focuses on portfolio health analytics, narrative generation, and orchestration of Azure services; it also handles Power BI embed configs and cross-domain scenario simulations.
- the System Health agent focuses on system health telemetry, alerts, and SLO monitoring; the Analytics Insights agent can consume these health signals as inputs to dashboards or narrative summaries.

**Handoff boundaries**

- the Analytics Insights agent remains the analytics/reporting orchestrator (dashboards, reports, narratives, scenario analysis, Power BI embedding).
- the System Health agent owns system health alerting, telemetry aggregation, and incident escalation workflows.

**Overlap with the Continuous Improvement agent (Continuous Improvement Process Mining)**

- the Continuous Improvement agent focuses on process mining and improvement opportunities; the Analytics Insights agent focuses on analytics consumption and storytelling.
- Handoff: the Continuous Improvement agent provides mined process insights and cycle-time metrics that the Analytics Insights agent can surface in dashboards and reports.

## Gaps, inconsistencies, and alignment needs

- **Naming/roles clarity**: Ensure documentation consistently assigns analytics ownership to the Analytics Insights agent and reserves system health telemetry and alerting for the System Health agent.
- **Action documentation vs. runtime behavior**: Ensure orchestration docs list the full action set (including ETL/power BI/realtime ingestion actions).
- **Event taxonomy alignment**: The analytics event topics list should be aligned with upstream agents’ emitted event names (schedule, deployment, risk, quality, resource).
- **Connector parity**: Ensure the Azure services referenced (Synapse, Data Factory, Event Hub, Power BI, OpenAI) have corresponding connectors and secrets defined in `ops/config/ops/config/.env.example` and runtime docs.
- **UI alignment**: Dashboard/report endpoints (`/dashboards/{id}`, `/reports/{id}/download`, `/narrative`) should match the frontend/API routing templates.

## Analytics output contract (checkpoint)

The analytics output contract is ready for execution when:

- The `action` list above is registered in orchestration routing.
- All outputs are produced with a `tenant_id` and timestamps.
- KPI alerts and insight events are emitted on the event bus with consistent payload schemas.
- Output stores (analytics outputs, alerts, lineage, events, KPI history, health snapshots) are reachable via configured state stores or database adapters.

## What's inside

- [src](/agents/operations-management/analytics-insights-agent/src): Implementation source for this component.
- [tests](/agents/operations-management/analytics-insights-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/operations-management/analytics-insights-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution. The agent subscribes to project health events to build portfolio-wide dashboards and reports, and it can invoke shared scenario simulations across domain agents.

## Full stack analytics architecture

The agent coordinates an Azure-first analytics stack:

- **Azure Synapse Analytics**: dedicated SQL pools and Spark pools for curated analytics using `SYNAPSE_WORKSPACE_NAME` and `SYNAPSE_SQL_POOL_NAME`.
- **Azure Data Lake Storage Gen2**: raw and curated datasets stored under `/raw/{source}` and `/curated/{domain}`.
- **Azure Machine Learning**: KPI prediction models (cost overrun, schedule slip) are trained and loaded at runtime.
- **Azure Data Factory**: orchestrates ETL pipelines from Planview, Jira, Workday, and SAP into Synapse.
- **Azure Event Hub + Stream Analytics**: real-time project/resource events streamed into Synapse.
- **Power BI Embedded**: report templates for health scores, risk distribution, and resource utilisation embedded via REST APIs.
- **Azure OpenAI**: narrative generation for insights delivered via the `/narrative` endpoint in the analytics service.
- **Azure Cognitive Services (Language/QnA Maker)**: natural language query support.
- **PostgreSQL/Cosmos DB**: audit storage for reports and narratives.

Key workflows now include:

- Provisioning Synapse pools, Data Lake file systems, and Data Factory pipelines via `provision_analytics_stack`.
- Ingesting Planview, Jira, Workday, and SAP data via `ingest_sources` and storing ingestion manifests in ADLS.
- Streaming real-time events through Event Hub and Stream Analytics with `ingest_realtime_event`.
- Generating monthly/periodic portfolio reports through `generate_periodic_report`, including trend/anomaly detection and recommendation outputs for the Continuous Improvement agent backlog ingestion.

## Continuous improvement loop integration (The Continuous Improvement agent handoff)

The Analytics Insights agent now supports a closed-loop handoff to 1. Build periodic analytics payloads using `generate_periodic_report`.
2. Include `project_metrics` in `filters` (e.g., `cycle_time_days`, `risk_occurrences`, `budget_variance_pct`, `late_task_ratio`, `scope_creep_count`).
3. The response includes:
   - `summary` rollups,
   - `trends` and `anomalies`,
   - `recommendations` for process change/training,
   - `report_id` for traceability.
4. Agent emits `analytics.periodic_report.generated` for downstream subscribers.

This output is designed to be consumed by the Continuous Improvement agent via `ingest_analytics_report`.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name analytics-insights-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/analytics-insights-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

Additional environment variables:

- `SYNAPSE_WORKSPACE_NAME`: Synapse workspace name.
- `SYNAPSE_SQL_POOL_NAME`: Dedicated SQL pool name.
- `DATA_LAKE_FILE_SYSTEM`: ADLS Gen2 file system name.
- `POWERBI_WORKSPACE_ID`: Power BI workspace for embedded reports.
- `POWERBI_CLIENT_ID`: Service principal/client id for Power BI embedding.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
