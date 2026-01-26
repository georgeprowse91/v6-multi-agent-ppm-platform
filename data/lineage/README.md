# Lineage Data Assets

## Purpose

Describe the lineage assets that support the canonical data model.

## What's inside

- `data/lineage/example-lineage.json`: JSON data asset or configuration.

## How it's used

These assets are referenced by connectors, services, and analytics pipelines.

## How to run / develop / test

Inspect YAML/JSON definitions and validate with relevant tooling as needed.

## Configuration

No runtime configuration; data assets are stored as versioned files.

## Troubleshooting

- Validation errors: ensure schema compatibility with `data/schemas/`.
- Missing assets: confirm the referenced file paths exist.
