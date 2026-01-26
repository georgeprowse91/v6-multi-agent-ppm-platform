# Documentation Hub

## Purpose

Describe the docs documentation set and link the narrative to the repo assets that implement it.

## What's inside

- `docs/agents`: Agent specs, prompts, or test assets.
- `docs/api`: API schemas and contracts.
- `docs/architecture`: Architecture narratives and diagrams.
- `docs/compliance`: Compliance guidance and requirements.
- `docs/connectors`: Connector documentation and integration guidance.
- `docs/data`: Data assets and fixtures for this component.
- `docs/methodology`: Methodology maps, stage gates, and templates.
- `docs/product`: Product documentation, including template catalog.
- `docs/templates`: Shared template library for agent artefacts.

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
