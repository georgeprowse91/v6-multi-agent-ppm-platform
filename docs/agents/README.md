# Agents Documentation

## Purpose

Describe the agents documentation set and link the narrative to the repo assets that implement it.

## What's inside

- [agent-catalog.md](/docs/agents/agent-catalog.md): Canonical inventory of platform agents and their responsibilities.

## How it's used

These documents are referenced by the root README and provide the canonical explanations for the platform architecture, data model, and operating procedures.

## Agent configuration reference

Agent runtime behavior is configured in `ops/config/agents/` (and mirrored into the agent runtime service at `services/agent-runtime/src/config/`) and loaded by the agent runtime service.

| File | Purpose | Key fields |
| --- | --- | --- |
| `ops/config/agents/orchestration.yaml` | Intent routing + response orchestration settings. | `intent_router.model.*`, `intent_router.intents`, `response_orchestration.max_concurrency`, `response_orchestration.retry_policy.*` |
| `ops/config/agents/intent-routing.yaml` | Intent definitions and routing targets. | `intents[].name`, `intents[].routes[].agent_id`, `intents[].routes[].action` |
| `ops/config/agents/portfolio.yaml` | Domain agent configuration for demand, business case, portfolio strategy, and program management. | `demand_intake.*`, `business_case.*`, `portfolio_strategy.*`, `program_management.*` |
| `config/agents/demo-participants.yaml` | Demo participant configuration for local and demo environments. | `participants[].name`, `participants[].role` |

## How to run / develop / test

Validate internal links across docs:

```bash
python scripts/check-links.py
```

## Configuration

No configuration. Documentation content lives in Markdown and YAML files under this folder.

## Troubleshooting

- Broken links: run the link checker and fix any relative path mismatches.
- Missing diagrams: verify files exist under `docs/architecture/diagrams/` where referenced.
