# Test Dependency Matrix

This matrix defines dependency sets used by CI and local test runs.

## CI profile: `all-optional`

The CI `test` job uses the `all-optional` profile. It installs:

- `requirements-dev.txt` (runtime + test tooling)
- Editable project install (`pip install -e .`)
- `email-validator` (optional import used by web governance tests)

This profile is expected to satisfy all dependency-based `pytest.importorskip(...)` and dependency guards in `tests/conftest.py`.

## Release-gate profile: `core`

Use this profile when running `make release-gate PROFILE=core` locally or in CI.

### Required install commands

```bash
make install-release-gate-core
```

This target installs:

- editable package with development + test extras (`pip install -e .[dev,test]`)
- release-gate unit/integration/security optional dependencies that are treated as required for core gating:
  - `slowapi`
  - `cryptography`
  - `sqlalchemy`
  - `alembic`
  - `celery`
  - `email-validator`

### Why these dependencies are mandatory for unit scope

`release-gate` runs `make test-unit`, `make test-integration`, and `make test-security`. Those test sets include modules guarded by `pytest.importorskip(...)` or collection-time dependency checks for the packages above. Installing them prevents false negatives caused by missing-dependency skips in strict CI skip mode.

`tests/integration/connectors/*` still requires OpenTelemetry packages, but these tests are excluded by default unless `ENABLE_CONNECTOR_INTEGRATION_TESTS` is set.

### Pytest plugin alignment

`pyproject.toml` configures pytest `timeout` options globally. Ensure pytest is invoked via the same interpreter environment used for installation (for example `python -m pytest`), so `pytest-timeout` from the `test` extra is discoverable.

## Dependency sets by test area

| Test area | Representative paths | Required dependency set |
| --- | --- | --- |
| Core/unit baseline | `tests/agents/`, `tests/ops/config/`, `tests/runtime/` | `requirements-dev.txt` |
| API security/rate limiting | `tests/apps/test_api_gateway_health.py`, `tests/security/test_auth_rbac.py` | baseline + `slowapi` |
| Crypto/security integration | `tests/security/test_auth_cache.py`, `tests/integration/test_data_lineage_service.py` | baseline + `cryptography` |
| Data migration/runtime integration | `tests/integration/test_data_migrations.py`, `tests/integration/test_orchestrator_persistence.py` | baseline + `sqlalchemy`, `alembic` |
| Workflow execution | `tests/integration/test_workflow_celery_execution.py` | baseline + `celery` |
| Web governance validation | `tests/apps/test_web_governance_api.py` | baseline + `email-validator` |
| Connector telemetry integrations | `tests/integration/connectors/*` | baseline + `opentelemetry-*` |

## Skip policy in CI

CI enables strict skip validation with:

- `PYTEST_FAIL_ON_UNEXPECTED_SKIPS=1`
- `pytest --fail-on-unexpected-skips`

Skip reasons are classified by `tests/conftest.py` into:

- `intentional_platform` (must include platform wording like `[platform]` or `requires linux`)
- `missing_dependency` (missing package/import wording)
- `unclassified`

In strict mode, any `missing_dependency` or `unclassified` skip fails CI.
