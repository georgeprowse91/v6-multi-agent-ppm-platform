# Methodology Library

## Purpose

Provide the canonical methodology maps, gate definitions, and templates used by agents to enforce governance across Agile, Waterfall, and Hybrid delivery.

## Architecture-level context

Methodology maps encode delivery stages as YAML (`map.yaml`) and define gate criteria in `gates.yaml`. The Approval Workflow agent (Agent 03) and Lifecycle & Governance agent (Agent 09) reference these definitions to enforce stage progression.

## Key folders

- `docs/methodology/agile/`
- `docs/methodology/waterfall/`
- `docs/methodology/hybrid/`

## Usage example

Inspect the Agile map:

```bash
sed -n '1,120p' docs/methodology/agile/map.yaml
```

## How to verify

List the templates for the Agile methodology:

```bash
ls docs/methodology/agile/templates
```

Expected output includes `sprint-plan.md`, `release-plan.md`, and `retro-notes.md`.

## Related docs

- [Methodology Overview](overview.md)
- [Agent Orchestration](../architecture/agent-orchestration.md)
