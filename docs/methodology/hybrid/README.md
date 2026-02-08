# Hybrid Documentation

## Purpose

Describe the hybrid documentation set and link the narrative to the repo assets that implement it.

## What's inside

- `docs/templates/`: Template library organized by discipline. Hybrid variants are labeled with
  the `-hybrid` suffix in the filename.
- `docs/methodology/hybrid/gates.yaml`: YAML definition or configuration used by this component.
- `docs/methodology/hybrid/map.yaml`: YAML definition or configuration used by this component.

## Stages & Activities

The hybrid methodology is defined in `docs/methodology/hybrid/map.yaml` and includes:

1. **Initiation & Governance Setup**: validate the business case and establish governance.
2. **Planning & Mobilization**: align milestones, risks, and communications cadence.
3. **Iterative Delivery**: plan iterations and manage scope changes.
4. **Integration & Release Readiness**: validate the integrated solution and release criteria.
5. **Transition & Closure**: complete closure reporting and compliance handover.

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
