# Agent Runtime Service

## Purpose

Hosts the multi-agent runtime that registers all 25 catalog agents, coordinates message
passing, and exposes orchestration + connector integration endpoints for the platform.

## Key capabilities

- Agent registry with all catalog agents loaded from `agents/`.
- Shared event bus for agent-to-agent messaging and orchestration telemetry.
- Connector registry integration and connector-backed action execution.
- Workflow engine integration for workflow-centric actions.
- FastAPI endpoints for orchestration configuration and runtime inspection.

## Endpoints

| Endpoint | Description |
| --- | --- |
| `GET /healthz` | Health check. |
| `GET /agents` | List registered agents. |
| `POST /agents/{agent_id}/execute` | Execute a specific agent with payload. |
| `GET /orchestration/config` | Read orchestration configuration. |
| `PUT /orchestration/config` | Update orchestration configuration. |
| `POST /orchestration/run` | Run orchestration using routing configuration. |
| `GET /connectors` | List connector registry entries. |
| `POST /connectors/{connector_id}/actions` | Execute a connector-backed action. |
| `POST /events/publish` | Publish an event to the runtime event bus. |
| `GET /events` | Inspect recent event bus activity. |

## Configuration

| Environment variable | Description | Default |
| --- | --- | --- |
| `AGENT_RUNTIME_DATA_DIR` | Directory for agent state stores. | `/tmp/agent-runtime-data` |
| `AGENT_RUNTIME_LLM_PROVIDER` | LLM provider for Intent Router. | `mock` |

## Running locally

```bash
python -m tools.component_runner run --type service --name agent-runtime --dry-run
```
