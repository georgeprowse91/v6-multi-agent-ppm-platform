# Formatting

Formatter wrapper that runs Ruff autofixes and Black with the repo defaults.

## Quickstart

```bash
python -m tools.format.run
```

## How to verify

Re-run the formatter after a clean run; it should exit 0 without additional changes.

## Key files

- `tools/format/run.py`: formatter wrapper entrypoint.
- `tools/format/format_config.yaml`: default format target paths.
- `pyproject.toml`: shared Ruff/Black settings.

## Example

Format only the API gateway and tests:

```bash
python -m tools.format.run --paths apps/api-gateway tests
```
