# Configuration

## Purpose

Explain configuration assets stored under `config/`.

## What's inside

- `config/agents`: Agent specs, prompts, or test assets.
- `config/connectors`: Connector documentation and integration guidance.
- `config/data-classification`: Subdirectory containing data classification assets for this area.
- `config/environments`: Subdirectory containing environments assets for this area.
- `config/feature-flags`: Subdirectory containing feature flags assets for this area.
- `config/rbac`: Subdirectory containing RBAC assets for this area.

## How it's used

Configuration files are loaded by apps, services, and agents at runtime.

## How to run / develop / test

Review configuration files directly before running services.

## Configuration

Edit the relevant YAML/JSON files and update `.env` values as needed.

## Troubleshooting

- Config not applied: ensure the runtime points to the correct file.
- Schema errors: validate configuration format with `python scripts/check-placeholders.py`.
