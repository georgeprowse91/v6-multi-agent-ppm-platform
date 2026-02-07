# Tests

## Overview

This directory contains the full test suite for the multi-agent PPM platform. Tests are organized by category, covering unit, integration, contract, end-to-end, load, performance, security, and policy validation.

## Directory structure

| Folder | Description |
| --- | --- |
| [agents/](./agents/) | Agent unit and integration tests |
| [apps/](./apps/) | Application-level tests |
| [connectors/](./connectors/) | Connector tests |
| [contract/](./contract/) | API contract tests |
| [docs/](./docs/) | Documentation tests |
| [e2e/](./e2e/) | End-to-end tests |
| [helpers/](./helpers/) | Test helper utilities |
| [integration/](./integration/) | Integration tests (includes integrations/connectors/ subdir) |
| [load/](./load/) | Load and performance tests |
| [performance/](./performance/) | Performance benchmarking tests |
| [policies/](./policies/) | Policy validation tests |
| [runtime/](./runtime/) | Runtime tests |
| [security/](./security/) | Security tests |
| [tools/](./tools/) | Tool tests |

## Key files

| File | Description |
| --- | --- |
| [conftest.py](./conftest.py) | Repo-wide pytest fixtures and configuration |
| [test_api.py](./test_api.py) | API endpoint tests |
| [test_event_contracts.py](./test_event_contracts.py) | Event contract validation tests |
| [test_schema_validation.py](./test_schema_validation.py) | Schema validation tests |
| [test_intent_router.py](./test_intent_router.py) | Intent router tests |
| [test_base_agent.py](./test_base_agent.py) | Base agent tests |
| [test_approval_workflow.py](./test_approval_workflow.py) | Approval workflow tests |
| [test_artifact_validation.py](./test_artifact_validation.py) | Artifact validation tests |
| [test_backup_runbook.py](./test_backup_runbook.py) | Backup runbook tests |
| [test_data_quality_rules.py](./test_data_quality_rules.py) | Data quality rule tests |
| [test_operational_runbooks.py](./test_operational_runbooks.py) | Operational runbook tests |

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
