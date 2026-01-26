# Packages

## Purpose

Describe shared packages and how they support platform services.

## What's inside

- `packages/canvas-engine`: Subdirectory containing canvas engine assets for this area.
- `packages/contracts`: Service contracts and schema artifacts.
- `packages/crypto`: Subdirectory containing crypto assets for this area.
- `packages/data-quality`: Subdirectory containing data quality assets for this area.
- `packages/llm`: Subdirectory containing LLM assets for this area.
- `packages/methodology-engine`: Subdirectory containing methodology engine assets for this area.

## How it's used

Packages are imported by apps, services, and agents across the repository.

## How to run / develop / test

Run unit tests (if present) or import modules in a Python shell:

```bash
pytest packages
```

## Configuration

Shared packages rely on repository-wide configuration in `.env` when needed.

## Troubleshooting

- Import errors: ensure the package is installed in editable mode (`make install-dev`).
- Missing dependencies: check `pyproject.toml` for required extras.
