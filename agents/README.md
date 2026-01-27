# Agents

## Purpose

Document the 25 specialized domain agents and how they integrate into the orchestration layer.

## What's inside

- `agents/core-orchestration`: Subdirectory containing core orchestration assets for this area.
- `agents/delivery-management`: Subdirectory containing delivery management assets for this area.
- `agents/operations-management`: Subdirectory containing operations management assets for this area.
- `agents/portfolio-management`: Subdirectory containing portfolio management assets for this area.
- `agents/common`: Shared utilities (metrics catalog, scenario engine, health recommendations).
- `agents/runtime`: Subdirectory containing runtime assets for this area.
- `agents/__init__.py`: Python module used by this component.

## How it's used

Agents are discovered by `tools/agent_runner` and referenced by the orchestration docs in `docs/agents/`.

## How to run / develop / test

```bash
python -m tools.agent_runner list-agents
```

## Configuration

Agent runtime settings live in `.env` (see `.env.example`) and shared config files under `config/`.

## Troubleshooting

- Agent not listed: ensure it lives under `agents/**/agent-*`.
- Runtime failures: verify required environment variables are set.
