# Modularization Standard

## Purpose
Define a component model so templates are assembled from reusable blocks instead of a monolithic `base.yaml`.

## Component Model

### Component IDs
- **Reusable blocks:** `assumptions`, `risks`, `milestones`, `benefits`, `controls`.
- **Template section components:** `core-<artefact>--<section-id>`.
- **Component instance IDs in manifests:**
  - For reusable blocks: `<artefact>--<section-id>`.
  - For one-off components: same as `component_id`.

### Interface Contract
Each component file in `docs/templates/components/*.yaml` must define:
- `component_id`
- `version`
- `kind` (`reusable-block` or `core-section`)
- `interface.inputs[]`
  - `name`: canonical input field
  - `source_placeholder`: placeholder token (for example `{{project_name}}`)
  - `required`: boolean
- `interface.outputs[]`
  - `name`: emitted section artifact
  - `type`: `section`
- `render`
  - `default_section` (reusable) or `section` (fully defined section)

### Composition Order
Each artefact manifest in `docs/templates/core/<artefact>/manifest.yaml` must define:
- `metadata`
- `inputs`
- `composition.order[]`, where each item has:
  - `component_instance_id`
  - `ref` (relative path to `docs/templates/components/*.yaml`)
  - `bind.section_id`

`composition.order` is authoritative and preserves the rendered section sequence.

## Reusable Blocks
Reusable components are stored at:
- `docs/templates/components/assumptions.yaml`
- `docs/templates/components/risks.yaml`
- `docs/templates/components/milestones.yaml`
- `docs/templates/components/benefits.yaml`
- `docs/templates/components/controls.yaml`

Use these blocks when a section intent matches, even if the section title varies across artefacts.

## Migration Rule
- Canonical core templates now use `manifest.yaml` in each `docs/templates/core/<artefact>/` directory.
- Extensions must target `core/<artefact>/manifest.yaml`.
