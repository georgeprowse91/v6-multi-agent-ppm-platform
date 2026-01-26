# Waterfall Documentation

## Purpose

Describe the waterfall documentation set and link the narrative to the repo assets that implement it.

## What's inside

- `docs/methodology/waterfall/templates`: Templates used by the component (deployment or message content).
- `docs/methodology/waterfall/gates.yaml`: YAML definition or configuration used by this component.
- `docs/methodology/waterfall/map.yaml`: YAML definition or configuration used by this component.

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
