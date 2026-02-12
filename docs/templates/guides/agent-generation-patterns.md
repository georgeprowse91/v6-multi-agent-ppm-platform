# Agent Generation Patterns

## Scope
This guide explains how agents should generate content from modular manifests in `docs/templates/core/*/manifest.yaml`.

## 1) Partial Generation
Use partial generation when only selected sections are requested.

Workflow:
1. Load manifest.
2. Resolve `composition.order` entries for requested `bind.section_id` values.
3. Hydrate only the matched components.
4. Render output with unchanged ordering from manifest for included sections.

Rules:
- Do not infer unreferenced sections.
- Keep unresolved placeholders verbatim for downstream completion.

## 2) Section-Level Regeneration
Use when a user requests updates to one section without changing the rest.

Workflow:
1. Identify section by `bind.section_id`.
2. Reload only that component reference.
3. Regenerate section using current inputs.
4. Replace section in-place; preserve neighboring sections and headings.

Rules:
- Keep the same `component_instance_id`.
- Preserve section order and unchanged sections byte-for-byte when possible.

## 3) Conflict Resolution
Conflicts can happen when reusable block defaults differ from section-specific expectations.

Priority order:
1. Manifest `bind` and local section intent.
2. Referenced component `render.section` overrides.
3. Reusable block `render.default_section`.

Resolution strategy:
- If section IDs conflict, keep manifest `bind.section_id` as canonical.
- If placeholders conflict, keep inputs explicitly listed in component `interface.inputs`.
- If two components target the same section in one manifest, keep first-in-order and emit a conflict note for maintainers.

## Operational Notes for Agents
- Prefer reusable components (`assumptions`, `risks`, `milestones`, `benefits`, `controls`) before creating new custom components.
- For new artefacts, create section components under `docs/templates/components/` and add references in `composition.order`.
- Do not write new monolithic `base.yaml` files for core artefacts.
