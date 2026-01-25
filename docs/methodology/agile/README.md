# Agile Methodology

## Purpose

Describe the Agile methodology map, stage gates, and templates used by agents to support sprint-based delivery.

## Architecture-level context

Agile maps define sprint cycles (Plan → Execute → Review → Retro). Gate checks ensure that Definition of Ready and Definition of Done criteria are met before advancing. YAML definitions are consumed by the workflow engine and approval agent.

## What the YAML means

- `map.yaml` defines the sprint stages, owners, and required artefacts.
- `gates.yaml` defines the criteria checked at sprint boundaries.

## Example workflow

1. **Sprint Planning**: validate backlog readiness and capacity.
2. **Execution**: track work item completion and quality checks.
3. **Review**: capture stakeholder feedback and accept stories.
4. **Retrospective**: record improvements and update process backlog.

## Usage example

Inspect the Agile map:

```bash
sed -n '1,120p' docs/methodology/agile/map.yaml
```

## How to verify

Check that sprint templates are available:

```bash
ls docs/methodology/agile/templates
```

Expected output includes `sprint-plan.md`, `release-plan.md`, and `retro-notes.md`.

## Implementation status

- **Implemented**: Agile map and templates.
- **Planned**: automated gate enforcement in the workflow engine.

## Related docs

- [Methodology Overview](../overview.md)
- [Approval Workflow Agent](../../architecture/agent-orchestration.md)
