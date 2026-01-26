# Agent 14: Quality Management Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 14: Quality Management. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/delivery-management/agent-14-quality-management/src`: Implementation source for this component.
- `agents/delivery-management/agent-14-quality-management/tests`: Test suites and fixtures.
- `agents/delivery-management/agent-14-quality-management/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-14-quality-management --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/agent-14-quality-management/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
