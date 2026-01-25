# Testing Package

Shared testing helpers intended for app and service test suites.

## Current state

- No implementation code yet in `packages/testing/`.
- Tests live under `tests/` and cover API, agent, and tooling behavior.

## Quickstart

Run the test suite:

```bash
make test
```

## How to verify

```bash
ls tests
```

Expected output includes unit tests and validation tests.

## Key files

- `tests/`: current test suite.
- `packages/testing/README.md`: scope and next steps.

## Example

Run a single test file:

```bash
pytest tests/test_api.py -v
```

## Next steps

- Add shared fixtures under `packages/testing/src/`.
- Consolidate common test helpers from `tests/conftest.py`.
