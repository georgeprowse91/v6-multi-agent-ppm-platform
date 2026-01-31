# Agent 12: Financial Management Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 12: Financial Management. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/delivery-management/agent-12-financial-management/src`: Implementation source for this component.
- `agents/delivery-management/agent-12-financial-management/tests`: Test suites and fixtures.
- `agents/delivery-management/agent-12-financial-management/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-12-financial-management --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/agent-12-financial-management/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

Additional configuration options supported by the Financial Management Agent:

- `exchange_rate_fixture`, `exchange_rate_api_url`: currency exchange sources.
- `tax_rate_fixture`, `tax_rate_api_url`: tax rate lookup configuration.
- `erp_pipelines`: list of Azure Data Factory pipelines to run for ERP ingestion.
- `service_bus`: `{ "connection_string": "...", "topic_name": "ppm-events" }` for financial event publishing.
- `key_vault`: `{ "vault_url": "...", "secrets": { "service_bus.connection_string": "secret-name" } }` to resolve credentials.
- `related_agent_endpoints`: `{ "resource_plan": "http://...", "schedule_progress": "http://...", "benefits": "http://..." }`.
- `related_agent_fixtures`: inline fixtures for local development and tests.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
