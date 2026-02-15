# Contract Tests

## Purpose

Document the contract test scope and how these checks validate the platform.

## What's inside

- [tests/contract/api-gateway-openapi.json](/tests/contract/api-gateway-openapi.json): JSON data asset or configuration.
- [tests/contract/test_api_contract.py](/tests/contract/test_api_contract.py): Python module used by this component.

## How it's used

These tests run under `pytest` and are included when executing `make test`.

## How to run / develop / test

```bash
pytest tests/contract
```

## Configuration

Tests use repo-wide fixtures in `tests/conftest.py` and environment variables from `.env`.

## Troubleshooting

- Import errors: install dev dependencies with `make install-dev`.
- Failing network calls: ensure dependent services are running or use mocks as defined in tests.
