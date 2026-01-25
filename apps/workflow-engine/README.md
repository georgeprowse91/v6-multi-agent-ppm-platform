# Workflow Engine

Workflow definitions and orchestration metadata used by the prototype and validation tooling.

## Current state

- Workflow definitions live in `apps/workflow-engine/workflows/`.
- Validation uses `scripts/validate-workflows.py` to ensure schemas and examples are consistent.
- There is no standalone service process yet; execution is modeled in the prototype UI.

## Quickstart

Validate workflow definitions:

```bash
python scripts/validate-workflows.py
```

## How to verify

```bash
ls apps/workflow-engine/workflows
```

Expected output includes workflow YAML files for intake and delivery flows.

## Key files

- `apps/workflow-engine/workflows/`: workflow definition YAMLs.
- `apps/web/ppm/workflows/engine.py`: prototype workflow runner.
- `scripts/validate-workflows.py`: workflow schema validation.

## Example

List the workflow IDs referenced by the prototype:

```bash
rg -n "id:" apps/workflow-engine/workflows
```

## Next steps

- Implement a dedicated workflow service under `apps/workflow-engine/src/`.
- Define persistence for workflow instances in `services/`.
