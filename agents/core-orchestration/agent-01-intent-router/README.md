# Agent 01: Intent Router Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 01: Intent Router. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/core-orchestration/agent-01-intent-router/src`: Implementation source for this component.
- `agents/core-orchestration/agent-01-intent-router/tests`: Test suites and fixtures.
- `agents/core-orchestration/agent-01-intent-router/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-01-intent-router --dry-run
```

Run unit tests (if present):

```bash
pytest agents/core-orchestration/agent-01-intent-router/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Routing configuration

Intent routing is defined in `config/agents/intent-routing.yaml`. The file declares each intent, minimum confidence thresholds, and the agent/action routes to invoke. Validate updates with:

```bash
python scripts/validate-intent-routing.py
```

### Adding a new intent (no code changes)

1. Add a new intent entry in `config/agents/intent-routing.yaml` with `name`, `min_confidence`, and at least one `routes` entry containing the target `agent_id` and optional `action`/`dependencies`.
2. Update the intent routing prompt if you need the LLM to recognize the new intent (`agents/runtime/prompts/examples/intent-router.prompt.yaml`).
3. Run `python scripts/validate-intent-routing.py` and update tests if you changed intent behavior.

### Migration notes

- The intent → agent/action mapping previously lived in `IntentRouterAgent._determine_agents`.
- Mapping updates now live in `config/agents/intent-routing.yaml`, so routing changes no longer require code changes.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
