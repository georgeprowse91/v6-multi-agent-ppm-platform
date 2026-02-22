# Api Documentation

## Purpose

Describe the api documentation set and link the narrative to the repo assets that implement it.

## What's inside

- [analytics-openapi.yaml](/docs/api/analytics-openapi.yaml): YAML definition or configuration used by this component.
- [auth.md](/docs/api/auth.md): Markdown documentation for this area.
- [connector-hub-openapi.yaml](/docs/api/connector-hub-openapi.yaml): YAML definition or configuration used by this component.
- [document-openapi.yaml](/docs/api/document-openapi.yaml): YAML definition or configuration used by this component.
- [event-contracts.md](/docs/api/event-contracts.md): Markdown documentation for this area.
- [graphql-schema.graphql](/docs/api/graphql-schema.graphql): File asset used by this component.

## How it's used

These documents are referenced by the root README and provide the canonical explanations for the platform architecture, data model, and operating procedures.

## How to run / develop / test

Validate internal links across docs:

```bash
python ops/scripts/check-links.py
```

## Configuration

No configuration. Documentation content lives in Markdown and YAML files under this folder.

## Troubleshooting

- Broken links: run the link checker and fix any relative path mismatches.
- Missing diagrams: verify files exist under `docs/architecture/diagrams/` where referenced.
