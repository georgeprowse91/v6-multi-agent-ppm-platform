# Llm Package

## Purpose

Describe the Llm shared package and how it supports platform services.

## What's inside

- `packages/llm/src`: Implementation source for this component.

## How it's used

Packages are imported by apps, services, and agents across the repository.

## How to run / develop / test

Run unit tests (if present) or import modules in a Python shell:

```bash
pytest packages/llm
```

## Configuration

Shared packages rely on repository-wide configuration in `.env` when needed.

## Troubleshooting

- Import errors: ensure the package is installed in editable mode (`make install-dev`).
- Missing dependencies: check `pyproject.toml` for required extras.
