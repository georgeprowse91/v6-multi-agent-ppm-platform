# Scripts

## Purpose

Catalog repository maintenance scripts used by CI and local development workflows.

## What's inside

- `scripts/check-links.py`: Python module used by this component.
- `scripts/check-migrations.py`: Python module used by this component.
- `scripts/check-placeholders.py`: Python module used by this component.
- `scripts/fix_docs_formatting.py`: Python module used by this component.
- `scripts/generate-sbom.py`: Python module used by this component.
- `scripts/init-db.sql`: Database migration or schema definition.

## How it's used

Scripts are called from the Makefile and CI workflows to validate docs and assets.

## How to run / develop / test

Run scripts directly with Python as needed.

## Configuration

Scripts rely on repository structure; no additional configuration required.

## Troubleshooting

- Script fails: ensure the required dependencies are installed.
- Path errors: run scripts from the repository root.
