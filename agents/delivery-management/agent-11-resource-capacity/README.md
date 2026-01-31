# Agent 11: Resource Capacity Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 11: Resource Capacity. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/delivery-management/agent-11-resource-capacity/src`: Implementation source for this component.
- `agents/delivery-management/agent-11-resource-capacity/tests`: Test suites and fixtures.
- `agents/delivery-management/agent-11-resource-capacity/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-11-resource-capacity --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/agent-11-resource-capacity/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Resource & Capacity Agent Environment Variables

**Identity & Notifications (Microsoft Graph)**
- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`: Azure AD application credentials.

**Azure Cognitive Search & OpenAI Embeddings**
- `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`, `AZURE_SEARCH_INDEX`
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

**Azure ML Model Registry**
- `AZURE_ML_ENDPOINT`, `AZURE_ML_API_KEY`

**Azure Service Bus**
- `AZURE_SERVICEBUS_CONNECTION_STRING`, `AZURE_SERVICEBUS_QUEUE_NAME`

**HRIS Integrations**
- Workday: `WORKDAY_API_URL`, `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`, `WORKDAY_TOKEN_URL`
- SAP SuccessFactors: `SF_API_SERVER`, `SF_CLIENT_ID`, `SF_CLIENT_SECRET`, `SF_REFRESH_TOKEN`, `SF_TOKEN_URL`

**Capacity Sources**
- Planview: `PLANVIEW_INSTANCE_URL`, `PLANVIEW_CLIENT_ID`, `PLANVIEW_CLIENT_SECRET`, `PLANVIEW_REFRESH_TOKEN`, `PLANVIEW_CAPACITY_ENDPOINT`
- Jira Tempo: `JIRA_TEMPO_API_URL`, `JIRA_TEMPO_API_TOKEN`

**Storage & Caching**
- `RESOURCE_CAPACITY_DATABASE_URL` (PostgreSQL SQLAlchemy URL)
- `REDIS_URL`

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
