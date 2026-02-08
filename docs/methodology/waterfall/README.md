# Waterfall Documentation

## Purpose

Describe the waterfall documentation set and link the narrative to the repo assets that implement it.

## What's inside

- `docs/templates/`: Template library organized by discipline. Waterfall variants are labeled with
  the `-waterfall` suffix in the filename.
- `docs/methodology/waterfall/gates.yaml`: YAML definition or configuration used by this component.
- `docs/methodology/waterfall/map.yaml`: YAML definition or configuration used by this component.

## Stages & Activities

The waterfall methodology is defined in `docs/methodology/waterfall/map.yaml` and includes:

1. **Initiation**: capture demand, build the business case, and approve the charter.
2. **Planning**: define scope, schedule, risk, and quality baselines.
3. **Execution**: deliver scope and manage change control.
4. **Monitoring & Control**: track performance, risks, and variance reporting.
5. **Closure**: capture outcomes, handover, and compliance artefacts.

Each stage enumerates tasks, owner roles, required artefacts, and exit criteria. Refer to the map
for the canonical task list and artefact requirements.

## How it's used

These documents are referenced by the root README and provide the canonical explanations for the platform architecture, data model, and operating procedures.

## How to run / develop / test

Validate internal links across docs:

```bash
python scripts/check-links.py
```

## Configuration

No configuration. Documentation content lives in Markdown and YAML files under this folder.

## Troubleshooting

- Broken links: run the link checker and fix any relative path mismatches.
- Missing diagrams: verify files exist under `docs/architecture/diagrams/` where referenced.
