# Connector SDK

## Purpose

Provide shared helpers and scaffolding for building connectors that conform to the platform manifest and mapping model.

## What's inside

- [integrations/connectors/sdk/tests/test_connector_runtime.py](/integrations/connectors/sdk/tests/test_connector_runtime.py): Python module used by this component.
- [integrations/connectors/sdk/tests/test_http_client.py](/integrations/connectors/sdk/tests/test_http_client.py): Python module used by this component.

## How it's used

The SDK is imported by connector implementations and validated in connector tests.

## How to run / develop / test

```bash
pytest integrations/connectors/sdk/tests
```

## Configuration

Configuration is inherited from the connector runtime and `.env` settings.

## Troubleshooting

- Import errors: install dev dependencies with `make install-dev`.
- Missing helper modules: ensure the SDK package path is correct.