# Linting

Lint wrapper for Ruff, Black (check mode), and Mypy with the same paths used in CI.

## Quickstart

```bash
python -m tools.lint.run
```

## How to verify

When everything is clean, the command exits with code 0 and prints:

```text
All checks passed!
```

## Key files

- `tools/lint/run.py`: entrypoint wiring Ruff/Black/Mypy.
- `tools/lint/lint_config.yaml`: default path list for linting.

## Example

Lint just the tests and tools directories:

```bash
python -m tools.lint.run --paths tests tools
```
