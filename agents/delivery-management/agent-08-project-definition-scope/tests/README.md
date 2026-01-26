# Agent 08: Project Definition Scope Tests

## Purpose

Hold test assets for Agent 08: Project Definition Scope to validate prompts, policies, and orchestration behavior.

## What's inside

- `README.md`: Documentation for this directory.

## How it's used

These tests are collected by `pytest` when running `make test` and help validate agent-specific behavior alongside shared agent runtime checks.

## How to run / develop / test

```bash
pytest agents/delivery-management/agent-08-project-definition-scope/tests
```

## Configuration

No component-specific configuration; tests rely on shared repo fixtures in `tests/` and `.env`.

## Troubleshooting

- No tests collected: add `test_*.py` modules alongside this README.
- Import errors: ensure the repo root is on `PYTHONPATH` (run from repo root).
