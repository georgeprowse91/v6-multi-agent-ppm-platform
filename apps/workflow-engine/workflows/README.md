# Workflow Definitions

## Purpose
Workflow definitions describe orchestration steps that the workflow engine executes. These YAML
files model tasks, decisions, and notifications used to route work between agents. The workflow
engine discovers definitions through `apps/workflow-engine/workflow_registry.py`.

## Responsibilities
- Define orchestrated sequences for intake, approvals, and escalation.
- Store workflow metadata (owner, version, description) for governance reviews.
- Provide schema-validated workflow definitions for execution.

## Folder structure
```
apps/workflow-engine/workflows/
├── README.md
├── definitions/
│   └── intake-triage.workflow.yaml
└── schema/
    └── workflow.schema.json
```

## Conventions
- Workflow files use the `.workflow.yaml` suffix.
- `metadata.name` should be unique across workflows.
- Each step must include a `next` field (or `null` when terminating).

## How to add a new workflow
1. Copy `definitions/intake-triage.workflow.yaml` and rename it.
2. Update the steps and agent actions.
3. Validate with the script below.
4. Confirm the new file is picked up by `apps/workflow-engine/workflow_registry.py`.

## How to validate/test
```bash
python scripts/validate-workflows.py apps/workflow-engine/workflows/definitions/intake-triage.workflow.yaml
```

## Example
```yaml
apiVersion: ppm.workflows/v1
kind: Workflow
metadata:
  name: intake-triage
  version: "1.0.0"
  owner: workflow-engine
steps:
  - id: capture-intake
    type: task
    next: evaluate-risk
```
