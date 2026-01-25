# Methodology Engine Package

Shared helpers for translating Agile/Waterfall/Hybrid templates into executable workflows.

## Current state

- No implementation code yet in `packages/methodology-engine/`.
- Methodology templates live under `docs/methodology/`.

## Quickstart

List methodology templates:

```bash
ls docs/methodology
```

## How to verify

```bash
ls docs/methodology/agile/templates
```

Expected output includes `sprint-plan.md` and other templates.

## Key files

- `docs/methodology/`: methodology templates.
- `packages/methodology-engine/README.md`: scope and next steps.

## Example

Search for the sprint goal section in the agile template:

```bash
rg -n "Sprint Goal" docs/methodology/agile/templates/sprint-plan.md
```

## Next steps

- Implement template parsing in `packages/methodology-engine/src/`.
- Map templates into workflow definitions under `apps/workflow-engine/workflows/`.
