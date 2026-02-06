# Agents

## Purpose

Document the 25 specialized domain agents and how they integrate into the orchestration layer.

## Directory structure

| Name | Description | Link |
|------|-------------|------|
| `core-orchestration` | Agents handling intent routing, response orchestration, and approval workflows. | [./core-orchestration/](./core-orchestration/) |
| `delivery-management` | Agents covering project definition, lifecycle governance, scheduling, resourcing, financials, vendor management, quality, risk, and compliance. | [./delivery-management/](./delivery-management/) |
| `operations-management` | Agents for change management, release deployment, knowledge management, process mining, stakeholder communications, analytics, data quality, and workflow engines. | [./operations-management/](./operations-management/) |
| `portfolio-management` | Agents for demand intake, business case analysis, portfolio strategy, and program management. | [./portfolio-management/](./portfolio-management/) |
| `common` | Shared utilities including metrics catalog, scenario engine, and health recommendations. | [./common/](./common/) |
| `runtime` | Runtime implementation, evaluation framework, and prompt templates. | [./runtime/](./runtime/) |

## Key files

| File | Description |
|------|-------------|
| `__init__.py` | Python package initialiser for the agents module. |
| `AGENT_CATALOG.md` | Generated catalogue enumerating agents, capabilities, and dependencies. |

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
