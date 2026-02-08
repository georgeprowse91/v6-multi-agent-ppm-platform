# Methodology Overview

## Purpose

Explain how methodology maps, stage gates, and templates are represented in the repository and used by agents to enforce governance.

## Architecture-level context

Methodology YAML files define stages and deliverables. The Approval Workflow agent (Agent 03) uses gate definitions to determine whether a stage can advance. The Workflow & Process Engine agent (Agent 24) executes gate checks and logs audit evidence.

## Map + gate structure

- `map.yaml`: ordered stages, required deliverables, and ownership.
- `gates.yaml`: gate criteria, approvals, and evidence requirements.
- `docs/templates/`: document templates for stage deliverables, organized by discipline with
  methodology variants labeled in the filename (e.g., `-agile`, `-hybrid`, `-waterfall`).

## YAML schema (v1)

All methodology YAML files follow the same minimal structure so the workflow engine and approval
agent can evaluate them consistently.

### `map.yaml`

```yaml
methodology: agile|waterfall|hybrid
version: "1.0"
stages:
  - id: discovery
    name: Discovery & Intake
    purpose: Why the stage exists and what success looks like.
    owner_roles: ["Role A", "Role B"]
    tasks:
      - id: capture-demand
        description: What must be done in this task.
        owner_roles: ["Role A"]
        artefacts:
          - name: Demand intake request
            template: docs/templates/portfolio-program/demand-intake-request-cross.md
            required: true
    exit_criteria:
      - Objective checks required to move to the next stage.
    next_stage: planning
```

### `gates.yaml`

```yaml
methodology: agile|waterfall|hybrid
version: "1.0"
gates:
  - id: gate-initiation
    name: Initiation Gate
    stage: discovery
    required_artefacts:
      - name: Business case
        template: docs/templates/portfolio-program/business-case-template-cross-var3.md
        evidence: Signed approval or ticket reference.
    criteria:
      - id: criteria-1
        description: Objective check that must pass.
        evidence: Link to evidence or report.
        check: "Approval workflow confirms sponsor sign-off."
    approvals:
      - role: Executive Sponsor
        approver: Agent 03 Approval Workflow
        required: true
    decision:
      approve: Proceed to planning.
      reject: Rework and resubmit.
```

## Diagram

```text
PlantUML: docs/architecture/diagrams/seq-stage-gate-enforcement.puml
```

## Usage example

Inspect Waterfall gate definitions:

```bash
sed -n '1,160p' docs/methodology/waterfall/gates.yaml
```

## How to verify

List methodology map files:

```bash
rg -n "map.yaml" docs/methodology
```

Expected output: map.yaml files for agile, waterfall, and hybrid.

## Implementation status

- **Implemented**: methodology YAMLs and templates.
- **Implemented**: runtime enforcement in the workflow engine through gate checks on workflow start/resume.

## Related docs

- [Agile Methodology](agile/README.md)
- [Waterfall Methodology](waterfall/README.md)
- [Hybrid Methodology](hybrid/README.md)
