# Tenants Configuration

## Purpose

Explain configuration assets stored under config/tenants.

## What's inside

- `config/tenants/default.yaml`: YAML definition or configuration used by this component.

## How it's used

Configuration files are loaded by apps, services, and agents at runtime.

## How to run / develop / test

Review configuration files directly before running services.

## Configuration

Edit the relevant YAML/JSON files and update `.env` values as needed.

## Troubleshooting

- Config not applied: ensure the runtime points to the correct file.
- Schema errors: validate configuration format with `python scripts/check-placeholders.py`.
