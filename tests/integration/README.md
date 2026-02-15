# Integration Tests

## Purpose

Document the integration test scope and how these checks validate the platform.

## What's inside

- [tests/integration/connectors](/tests/integration/connectors): Connector documentation and integration guidance.
- [tests/integration/test_orchestrator_persistence.py](/tests/integration/test_orchestrator_persistence.py): Python module used by this component.
- [tests/integration/test_workflow_engine_runtime.py](/tests/integration/test_workflow_engine_runtime.py): Python module used by this component.
- [tests/integration/test_multi_agent_flows.py](/tests/integration/test_multi_agent_flows.py): End-to-end multi-agent orchestration flows using async mocks.

## How it's used

These tests run under `pytest` and are included when executing `make test`.

## How to run / develop / test

```bash
pytest tests/integration
pytest tests/integration/test_multi_agent_flows.py
```

## Configuration

Tests use repo-wide fixtures in `tests/conftest.py` and environment variables from `.env`.

## Troubleshooting

- Import errors: install dev dependencies with `make install-dev`.
- Failing network calls: ensure dependent services are running or use mocks as defined in tests.
