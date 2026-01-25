# Methodology Overview

## Purpose

Explain how methodology maps, stage gates, and templates are represented in the repository and used by agents to enforce governance.

## Architecture-level context

Methodology YAML files define stages and deliverables. The Approval Workflow agent (Agent 03) uses gate definitions to determine whether a stage can advance. The Workflow & Process Engine agent (Agent 24) executes gate checks and logs audit evidence.

## Map + gate structure

- `map.yaml`: ordered stages, required deliverables, and ownership.
- `gates.yaml`: gate criteria, approvals, and evidence requirements.
- `templates/`: document templates for stage deliverables.

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
- **Planned**: runtime enforcement in the workflow engine.

## Related docs

- [Agile Methodology](agile/README.md)
- [Waterfall Methodology](waterfall/README.md)
- [Hybrid Methodology](hybrid/README.md)
