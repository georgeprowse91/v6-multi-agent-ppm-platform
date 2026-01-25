# Waterfall Methodology

## Purpose

Describe the Waterfall methodology map, stage gates, and templates used for sequential delivery.

## Architecture-level context

Waterfall stages (Initiation → Planning → Execution → Monitoring → Closing) are encoded in `map.yaml`. Gate checks in `gates.yaml` ensure governance artifacts (charter, budget approval, QA plan) are complete before advancing.

## What the YAML means

- `map.yaml`: sequential phases and required deliverables.
- `gates.yaml`: approval criteria and evidence requirements.

## Example workflow

1. **Initiation**: demand intake, charter creation, sponsor approval.
2. **Planning**: baseline schedule, budget, and resourcing.
3. **Execution**: deliverables tracked and risks managed.
4. **Monitoring**: status reports and variance reviews.
5. **Closing**: post-implementation review and archive.

## Usage example

Inspect the Waterfall gates:

```bash
sed -n '1,160p' docs/methodology/waterfall/gates.yaml
```

## How to verify

List Waterfall templates:

```bash
ls docs/methodology/waterfall/templates
```

Expected output includes `project-charter.md`, `schedule-baseline.xlsx`, and `wbs.yaml`.

## Implementation status

- **Implemented**: Waterfall map, gates, templates.
- **Planned**: gate automation with approvals and audit evidence.

## Related docs

- [Methodology Overview](../overview.md)
- [Project Definition Agent](../../agents/agent-catalog.md)
