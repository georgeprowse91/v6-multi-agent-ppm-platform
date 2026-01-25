# Linting

Lint checks mirror the CI expectations: Ruff, Black (check mode), and Mypy.
Defaults are stored in `tools/lint/lint_config.yaml`.

## Usage

```bash
python -m tools.lint.run
```

To lint a subset of paths:

```bash
python -m tools.lint.run --paths agents apps packages
```
