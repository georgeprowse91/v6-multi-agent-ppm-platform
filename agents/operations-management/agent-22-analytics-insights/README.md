# Agent 22: Analytics Insights Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 22: Analytics Insights. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/operations-management/agent-22-analytics-insights/src`: Implementation source for this component.
- `agents/operations-management/agent-22-analytics-insights/tests`: Test suites and fixtures.
- `agents/operations-management/agent-22-analytics-insights/Dockerfile`: Container build recipe for local or CI use.

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

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-22-analytics-insights --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/agent-22-analytics-insights/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

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
