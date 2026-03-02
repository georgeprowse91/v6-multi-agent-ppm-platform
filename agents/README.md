# Agents

## Purpose

Document the 25 specialized domain agents and how they integrate into the orchestration layer.

## Directory structure

| Name | Description | Link |
|------|-------------|------|
| `core-orchestration` | Agents handling intent routing, response orchestration, and approval workflows. | [](/./core-orchestration/) |
| `delivery-management` | Agents covering project definition, lifecycle governance, scheduling, resourcing, financials, vendor management, quality, risk, and compliance. | [](/./delivery-management/) |
| `operations-management` | Agents for change management, release deployment, knowledge management, process mining, stakeholder communications, analytics, data quality, and system health. | [](/./operations-management/) |
| `portfolio-management` | Agents for demand intake, business case analysis, portfolio strategy, and program management. | [](/./portfolio-management/) |
| `common` | Shared utilities including metrics catalog, scenario engine, and health recommendations. | [](/./common/) |
| `runtime` | Runtime implementation, evaluation framework, and prompt templates. | [](/./runtime/) |

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

## Agent metadata generation

The agent catalog markdown and the web UI metadata JSON are generated from the
individual agent README files. After editing any `agents/**/*-agent/README.md`,
refresh the outputs with:

```bash
python scripts/generate_agent_metadata.py
```

To verify the committed files are up to date (e.g., in CI), run:

```bash
python scripts/generate_agent_metadata.py --check
```

## Configuration

Agent runtime settings live in `.env` (see `ops/config/.env.example`) and shared config files under `config/`.

## Troubleshooting

- Agent not listed: ensure it lives under `agents/**/*-agent`.
- Runtime failures: verify required environment variables are set.
