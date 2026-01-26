# Load Tests

## Purpose

Document the load test scope and how these checks validate the platform.

## What's inside

- `tests/load/sla_targets.json`: Load-test SLA profiles and thresholds.
- `tests/load/test_load_sla.py`: Load-test SLA validation suite.

## How it's used

These tests run under `pytest` and are included when executing `make test`.

## How to run / develop / test

```bash
pytest tests/load
```

## Configuration

Tests use repo-wide fixtures in `tests/conftest.py` and environment variables from `.env`.

## Troubleshooting

- Import errors: install dev dependencies with `make install-dev`.
- Failing network calls: ensure dependent services are running or use mocks as defined in tests.
