# Agent 25: Analytics Insights Specification

## Purpose

Provide a central analytics agent that aggregates platform telemetry, computes KPIs, runs predictive
analytics, and publishes recommendations for downstream agents and dashboards.

## What's inside

- `agents/operations-management/agent-25-analytics-insights/src`: Implementation source for this component.
- `agents/operations-management/agent-25-analytics-insights/tests`: Test suites and fixtures.
- `agents/operations-management/agent-25-analytics-insights/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing analytics requests. The agent
subscribes to project, resource, quality, and risk events to maintain near-real-time KPIs and
publishes insights back onto the event bus.

## Key responsibilities

- Aggregate and store analytics events/metrics in Synapse and the analytics datastore.
- Maintain KPI definitions for schedule adherence, cost variance, program performance, resource
  utilisation, defect density, risk exposure, compliance levels, and system health.
- Execute batch and streaming KPI updates using Spark or streaming pipelines.
- Train and serve predictive models for project success, risk escalation, and resource bottlenecks.
- Provide APIs for dashboards and agents to query metrics, trends, and forecasts.
- Enforce data privacy via redaction/anonymisation.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-25-analytics-insights --dry-run
```

Run unit tests:

```bash
pytest agents/operations-management/agent-25-analytics-insights/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings
such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`.

Additional environment variables:

- `SYNAPSE_WORKSPACE_NAME`: Synapse workspace name.
- `SYNAPSE_SQL_POOL_NAME`: Dedicated SQL pool name.
- `DATA_LAKE_FILE_SYSTEM`: ADLS Gen2 file system name.
- `POWERBI_WORKSPACE_ID`: Power BI workspace for embedded reports.
- `POWERBI_CLIENT_ID`: Service principal/client id for Power BI embedding.
