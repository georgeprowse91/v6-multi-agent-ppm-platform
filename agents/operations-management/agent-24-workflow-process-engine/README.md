# Agent 24: Workflow Process Engine Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 24: Workflow Process Engine. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/operations-management/agent-24-workflow-process-engine/src`: Implementation source for this component.
- `agents/operations-management/agent-24-workflow-process-engine/tests`: Test suites and fixtures.
- `agents/operations-management/agent-24-workflow-process-engine/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-24-workflow-process-engine --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/agent-24-workflow-process-engine/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Durable workflow configuration

The agent loads durable workflow orchestration definitions from `config/agent-24/durable_workflows.yaml` on startup. Each workflow entry defines ordered steps, retry policies, and optional compensation tasks. The agent registers these definitions as Durable Functions-style orchestrations and persists them in the workflow state store.

### BPMN 2.0 support

The engine can parse BPMN 2.0 XML definitions and convert them into Durable Functions-style orchestrations. Use the `/workflows/upload` API (in the orchestration service) to upload BPMN files for deployment. BPMN user tasks become `human` tasks; service/script tasks become `automated` tasks. The parser uses `bpmn-python` when available and falls back to an XML parser.

### Database schema

When configured with a database backend, the agent persists workflow metadata in PostgreSQL tables:

- `workflow_definitions`: stores workflow definitions and metadata (`workflow_id`, name, version, JSON definition payload).
- `workflow_runs`: stores workflow instance payloads, status, and checkpoint metadata.

### Observability & integrations

The agent emits workflow events to Azure Service Bus, Azure Monitor telemetry, and Azure Event Grid topics (via the event bus wrapper). It also supports triggering Azure Logic Apps tasks and Durable Functions-style retries and compensation flows.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
