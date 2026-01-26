# Security Tests

## Purpose

Document the security test scope and how these checks validate the platform.

## What's inside

- `tests/security/test_auth_rbac.py`: Python module used by this component.
- `tests/security/test_downstream_auth.py`: Python module used by this component.
- `tests/security/test_field_level_masking.py`: Python module used by this component.
- `tests/security/test_lineage_masking.py`: Python module used by this component.
- `tests/security/test_policy_engine_integration.py`: Python module used by this component.
- `tests/security/test_rate_limit_cors.py`: Python module used by this component.

## How it's used

These tests run under `pytest` and are included when executing `make test`.

## How to run / develop / test

```bash
pytest tests/security
```

## Configuration

Tests use repo-wide fixtures in `tests/conftest.py` and environment variables from `.env`.

## Troubleshooting

- Import errors: install dev dependencies with `make install-dev`.
- Failing network calls: ensure dependent services are running or use mocks as defined in tests.
