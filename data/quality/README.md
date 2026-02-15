# Quality Data Assets

## Purpose

Describe the quality assets that support the canonical data model.

## What's inside

- [rules.yaml](/data/quality/rules.yaml): YAML definition or configuration used by this component.

## How it's used

These assets are referenced by connectors, services, and analytics pipelines.

## How to run / develop / test

Inspect YAML/JSON definitions and validate with relevant tooling as needed.

## Configuration

No runtime configuration; data assets are stored as versioned files.

## Troubleshooting

- Validation errors: ensure schema compatibility with `data/schemas/`.
- Missing assets: confirm the referenced file paths exist.
