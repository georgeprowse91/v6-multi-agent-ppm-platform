# Migrations Data Assets

## Purpose

Describe the migrations assets that support the canonical data model.

## What's inside

- [versions](/data/migrations/versions): Subdirectory containing versions assets for this area.
- [env.py](/data/migrations/env.py): Python module used by this component.
- [models.py](/data/migrations/models.py): Python module used by this component.
- [validate_registry_consistency.py](/data/migrations/validate_registry_consistency.py): Consistency checker for migration/model/schema registry alignment.

## How it's used

These assets are referenced by connectors, services, and analytics pipelines.

## How to run / develop / test

- Validate migration prefix ordering: `python ops/scripts/check-migrations.py`
- Validate DB/schema-registry consistency: `python data/migrations/validate_registry_consistency.py`
- Apply migrations: `alembic upgrade head`

## Configuration

No runtime configuration; data assets are stored as versioned files.

## Troubleshooting

- Validation errors: ensure schema compatibility with `data/schemas/`.
- Missing assets: confirm the referenced file paths exist.
