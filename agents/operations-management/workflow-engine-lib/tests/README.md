# Workflow Engine Library Tests

Tests for the workflow engine library (workflow spec parsing, state store, task queue, BPMN import, event criteria matching).

## How to run

```bash
pytest agents/operations-management/workflow-engine-lib/tests
```

## Troubleshooting

- No tests collected: add `test_*.py` modules alongside this README.
- Import errors: ensure the repo root is on `PYTHONPATH` (run from repo root).
