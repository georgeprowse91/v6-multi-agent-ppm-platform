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

- `PERFORMANCE_BASE_URL`: Base URL for the target environment (defaults to the staging API gateway).
- `PERFORMANCE_AUTH_TOKEN`: Optional bearer token used for authenticated endpoints.
- `PERFORMANCE_TENANT_ID`: Optional tenant identifier header for authenticated endpoints.
- `LOAD_PROFILE`: Selects SLA profile (`ci`, `staging`, `production`).
- `LOAD_TARGET`: Selects a specific target from `sla_targets.json`.

## Troubleshooting

- Import errors: install dev dependencies with `make install-dev`.
- Failing network calls: ensure the target environment is reachable and credentials are configured.
