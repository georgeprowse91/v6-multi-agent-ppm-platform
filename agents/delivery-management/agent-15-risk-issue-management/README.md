# Agent 15: Risk Issue Management Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 15: Risk Issue Management. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/delivery-management/agent-15-risk-issue-management/src`: Implementation source for this component.
- `agents/delivery-management/agent-15-risk-issue-management/tests`: Test suites and fixtures.
- `agents/delivery-management/agent-15-risk-issue-management/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-15-risk-issue-management --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/agent-15-risk-issue-management/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

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
