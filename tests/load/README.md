# Load tests

This directory contains load tests for the platform.

## Scope
- Test modules that exercise the platform's cross-cutting behavior.
- Fixtures, helpers, and sample payloads needed for these tests.
- Any contract or environment notes required to run them locally.

## SLA targets
Load profiles are defined in `tests/load/sla_targets.json` and enforced in `tests/load/test_load_sla.py`.
Use the `LOAD_PROFILE` environment variable to select a profile (defaults to `ci`).

## Running locally
```bash
pytest tests/load
```

To run the standalone load runner against a live environment:
```bash
LOAD_PROFILE=production python scripts/load-test.py --profile tests/load/sla_targets.json --target https://api.example.com/healthz
```
