# Examples

## Purpose
This folder contains runnable, validated examples used in documentation and demos. Each example is
paired with a schema or validator so it can be checked in CI.

## Responsibilities
- Provide canonical JSON/YAML examples for onboarding and demos.
- Keep examples validated against schemas in this repository.
- Showcase how agents and services expect payloads.

## Folder structure
```
examples/
├── README.md
├── portfolio-intake-request.json
├── schema/
│   └── portfolio-intake.schema.json
└── workflows/
    └── portfolio-intake.workflow.yaml
```

## Conventions
- Example payloads should be minimal but complete.
- JSON examples must match their schemas in `examples/schema`.
- Workflow examples reuse the workflow engine schema in `apps/workflow-engine/workflows/schema/`.

## How to add a new example
1. Add a schema under `examples/schema/` if one does not exist.
2. Create the example JSON/YAML file in this folder or a subfolder.
3. Register the new example in the validator script (e.g. `scripts/validate-examples.py`).
4. Run validation commands below.

## How to validate/test
```bash
python scripts/validate-examples.py examples/portfolio-intake-request.json
python scripts/validate-workflows.py examples/workflows/portfolio-intake.workflow.yaml
```

## Example
```json
{
  "request_id": "req-2024-09-001",
  "portfolio_id": "portfolio-apollo",
  "summary": "New analytics program for enterprise reporting.",
  "owner": "portfolio.manager@ppm.example",
  "priority": "high",
  "tags": ["analytics", "apollo"]
}
```
