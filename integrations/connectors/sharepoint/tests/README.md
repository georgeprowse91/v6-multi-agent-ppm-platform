# Sharepoint Connector Test Assets

## Purpose

Store fixtures and connector-level test scaffolding for the Sharepoint integration.

## What's inside

- [fixtures](/integrations/connectors/sharepoint/tests/fixtures): Subdirectory containing fixtures assets for this area.

## How it's used

Fixtures in this folder are used by integration tests under `tests/integration/` or by connector-specific test modules as they are added.

## How to run / develop / test

```bash
pytest integrations/connectors/sharepoint/tests
```

## Configuration

No component-specific configuration; fixture files are loaded from disk by tests.

## Troubleshooting

- Pytest reports zero tests: this folder may contain fixtures only.
- File not found errors: verify fixture paths in the integration tests.
