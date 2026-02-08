# Agile Documentation

## Purpose

Describe the agile documentation set and link the narrative to the repo assets that implement it.

## What's inside

- `docs/templates/`: Template library organized by discipline. Agile variants are labeled with
  the `-agile` suffix in the filename.
- `docs/methodology/agile/gates.yaml`: YAML definition or configuration used by this component.
- `docs/methodology/agile/map.yaml`: YAML definition or configuration used by this component.

## Stages & Activities

The agile methodology is defined in `docs/methodology/agile/map.yaml` and includes:

1. **Intake & Discovery**: capture demand, build the business case, and seed the backlog.
2. **Sprint & Release Planning**: define sprint commitments and release readiness.
3. **Sprint Execution & Delivery**: deliver backlog items and track change impacts.
4. **Review & Release Readiness**: validate acceptance criteria and release readiness.
5. **Retrospective & Improvement**: capture lessons learned and improvement actions.

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
