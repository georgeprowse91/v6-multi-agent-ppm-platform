# E2E Tests

## Purpose

Document the e2e test scope and how these checks validate the platform.

## What's inside

- [test_acceptance_scenarios.py](/tests/e2e/test_acceptance_scenarios.py): Python module used by this component.
- [test_user_journey.py](/tests/e2e/test_user_journey.py): Python module used by this component.
- [test_web_login.py](/tests/e2e/test_web_login.py): Python module used by this component.

## How it's used

These tests run under `pytest` and are included when executing `make test`.

## How to run / develop / test

```bash
pytest tests/e2e
```

## Configuration

Tests use repo-wide fixtures in `tests/conftest.py` and environment variables from `.env`.

## Troubleshooting

- Import errors: install dev dependencies with `make install-dev`.
- Failing network calls: ensure dependent services are running or use mocks as defined in tests.
