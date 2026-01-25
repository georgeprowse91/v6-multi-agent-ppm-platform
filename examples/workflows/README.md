# Workflow Examples

## Purpose
These workflow examples demonstrate how to model orchestration steps for demos and documentation.
They reuse the workflow engine schema to stay consistent with production definitions.

## Responsibilities
- Provide sample workflow YAML for documentation walkthroughs.
- Keep example workflows validated against the workflow schema.
- Illustrate best practices for naming and step ordering.

## Folder structure
```
examples/workflows/
├── README.md
├── portfolio-intake.workflow.yaml
├── ../../apps/workflow-engine/workflows/definitions/intake-triage.workflow.yaml
├── ../../apps/workflow-engine/workflows/schema/workflow.schema.json
└── ../../apps/workflow-engine/workflows/README.md
```

## Conventions
- Use `.workflow.yaml` suffix.
- Keep `metadata.owner` as `examples` for sample definitions.
- Ensure all `steps` include a `next` pointer or `null` termination.

## How to add a new workflow example
1. Copy `portfolio-intake.workflow.yaml` and update metadata and steps.
2. Run the workflow validation script.
3. Reference the example in docs that describe workflow behavior.

## How to validate/test
```bash
python scripts/validate-workflows.py examples/workflows/portfolio-intake.workflow.yaml
```

## Example
```yaml
apiVersion: ppm.workflows/v1
kind: Workflow
metadata:
  name: portfolio-intake
  version: "1.0.0"
  owner: examples
steps:
  - id: record-request
    type: task
    next: notify-pmo
```
