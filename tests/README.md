# Tests

## Purpose

Document the full test suite and how these checks validate the platform.

## What's inside

- `tests/agents`: Subdirectory containing agent test assets for this area.
- `tests/contract`: Subdirectory containing contract assets for this area.
- `tests/e2e`: End-to-end test specs or tooling.
- `tests/integration`: Subdirectory containing integration assets for this area.
- `tests/load`: Subdirectory containing load assets for this area.
- `tests/policies`: Subdirectory containing policy assets for this area.
- `tests/security`: Subdirectory containing security assets for this area.

## How it's used

These tests run under `pytest` and are included when executing `make test`.

## How to run / develop / test

```bash
pytest tests
```

## Configuration

Tests use repo-wide fixtures in `tests/conftest.py` and environment variables from `.env`.

## Troubleshooting

- Import errors: install dev dependencies with `make install-dev`.
- Failing network calls: ensure dependent services are running or use mocks as defined in tests.
