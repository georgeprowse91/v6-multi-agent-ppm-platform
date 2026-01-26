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

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
