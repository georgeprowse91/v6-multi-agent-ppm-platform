# Agent 23: Data Synchronisation Quality Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 23: Data Synchronisation Quality. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/operations-management/agent-23-data-synchronisation-quality/src`: Implementation source for this component.
- `agents/operations-management/agent-23-data-synchronisation-quality/tests`: Test suites and fixtures.
- `agents/operations-management/agent-23-data-synchronisation-quality/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-23-data-synchronisation-quality --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/agent-23-data-synchronisation-quality/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Required environment variables

Set the following variables to enable full integration:

**Azure Service Bus / Event Grid**
- `AZURE_SERVICE_BUS_CONNECTION_STRING`
- `AZURE_SERVICE_BUS_TOPIC_NAME` (optional, defaults to `ppm-events`)
- `AZURE_SERVICE_BUS_QUEUE_NAME` (optional, defaults to `ppm-sync-queue`)
- `EVENT_GRID_ENDPOINT`
- `EVENT_GRID_KEY`

**Azure Data Stores**
- `SQL_CONNECTION_STRING`
- `COSMOS_ENDPOINT`
- `COSMOS_KEY`

**Azure Data Factory & Functions**
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_DATA_FACTORY_NAME`
- `AZURE_FUNCTION_BASE_URL` (Function App base URL for ETL/transformations)
- `AZURE_FUNCTION_KEY` (optional, function key for secured endpoints)
- `AZURE_KEY_VAULT_URL`

**Azure Monitor / Log Analytics**
- `LOG_ANALYTICS_ENDPOINT`
- `LOG_ANALYTICS_RULE_ID`
- `LOG_ANALYTICS_STREAM_NAME` (optional, defaults to `DataSyncLatency`)

**Connector Credentials (stored in Azure Key Vault or set locally)**
- `PLANVIEW_CLIENT_ID`, `PLANVIEW_CLIENT_SECRET`, `PLANVIEW_REFRESH_TOKEN`, `PLANVIEW_INSTANCE_URL`
- `SAP_USERNAME`, `SAP_PASSWORD`, `SAP_URL`
- `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_INSTANCE_URL`
- `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`, `WORKDAY_API_URL`

### Local development

1. Copy `.env.example` to `.env` and populate the required variables above.
2. Ensure the validation rules and pipeline configuration files exist:
   - `config/agent-23/validation_rules.yaml`
   - `config/agent-23/pipelines.yaml`
   - `config/agent-23/schema_registry.yaml`
   - `config/agent-23/mapping_rules.yaml`
   - `config/agent-23/quality_thresholds.yaml`
3. If you want to invoke Azure Functions locally, expose the Function App base URL and key in `.env`.
4. Run the agent locally:

```bash
python -m tools.agent_runner run-agent --name agent-23-data-synchronisation-quality --dry-run
```

### Production deployment

1. Provision Azure Service Bus, Event Grid, Data Factory, SQL Database, Cosmos DB, and Log Analytics.
2. Store connector secrets in Azure Key Vault and grant the agent identity access to the vault.
3. Provide the environment variables above through your runtime (Kubernetes secrets, App Service settings, or managed identity configuration).
4. Deploy with the provided Dockerfile or orchestration tooling in `infra/`.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.

## Events emitted

The agent publishes the following Service Bus events during synchronization:

- `sync.start` when a synchronization begins
- `sync.complete` on success, failure, or duplicate detection
- `conflict.detected` when update conflicts are recorded
