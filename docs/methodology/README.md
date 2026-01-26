# Methodology Documentation

## Purpose

Describe the methodology documentation set and link the narrative to the repo assets that implement it.

## What's inside

- `docs/methodology/agile`: Subdirectory containing agile assets for this area.
- `docs/methodology/hybrid`: Subdirectory containing hybrid assets for this area.
- `docs/methodology/waterfall`: Subdirectory containing waterfall assets for this area.
- `docs/methodology/overview.md`: Markdown documentation for this area.

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
