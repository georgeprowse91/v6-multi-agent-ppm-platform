# Migrations Data Assets

## Purpose

Describe the migrations assets that support the canonical data model.

## What's inside

- `data/migrations/versions`: Subdirectory containing versions assets for this area.
- `data/migrations/env.py`: Python module used by this component.
- `data/migrations/models.py`: Python module used by this component.

## How it's used

These assets are referenced by connectors, services, and analytics pipelines.

## How to run / develop / test

Inspect YAML/JSON definitions and validate with relevant tooling as needed.

## Configuration

No runtime configuration; data assets are stored as versioned files.

## Troubleshooting

- Validation errors: ensure schema compatibility with `data/schemas/`.
- Missing assets: confirm the referenced file paths exist.
