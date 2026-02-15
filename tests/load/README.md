# Load Tests

## Purpose

Document the load test scope and how these checks validate the platform.

## What's inside

- [sla_targets.json](/tests/load/sla_targets.json): Load-test SLA profiles and thresholds, including multi-agent flow targets.
- [multi_agent_scenarios.py](/tests/load/multi_agent_scenarios.py): Scenario builder for single-endpoint and orchestrated multi-step flows.
- [test_load_sla.py](/tests/load/test_load_sla.py): Load-test SLA validation suite with per-step assertions.
- [test_connectors_latency_sla.py](/tests/load/test_connectors_latency_sla.py): Multi-agent risk/compliance/approval SLA coverage.

## How it's used

These tests run under `pytest` and are included when executing `make test`.

## How to run / develop / test

```bash
pytest tests/load
pytest tests/load/test_load_sla.py
LOAD_TARGET=project-definition-schedule-resource-flow pytest tests/load/test_load_sla.py
LOAD_TARGET=risk-compliance-approval-flow pytest tests/load/test_connectors_latency_sla.py
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
