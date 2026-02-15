# Data Documentation

## Purpose

Describe the data documentation set and link the narrative to the repo assets that implement it.

## What's inside

- [docs/data/data-model.md](/docs/data/data-model.md): Markdown documentation for this area.
- [docs/data/data-quality.md](/docs/data/data-quality.md): Markdown documentation for this area.
- [docs/data/lineage.md](/docs/data/lineage.md): Markdown documentation for this area.

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
