# Developer Tooling

Repo-aware tooling for formatting, linting, code generation, and local dev helpers used by
the Makefile and CI pipelines.

## Quickstart

```bash
make lint
make format
make codegen
```

For the local dev stack:

```bash
bash tools/local-dev/dev_up.sh
```

## How to verify

```bash
python -m tools.lint.run
```

Expected output (when lint is clean):

```text
All checks passed!
```

```bash
python -m tools.codegen.run
```

Expected output:

```text
Generated OpenAPI summary at apps/api-gateway/openapi.
```

## Key files

- `tools/lint/run.py`: Ruff + Black + Mypy entrypoint.
- `tools/format/run.py`: Ruff + Black formatter wrapper.
- `tools/codegen/run.py`: OpenAPI validation + summary outputs.
- `tools/local-dev/dev_up.sh`: Docker Compose wrapper for local stack.

## Example

Lint only the API gateway sources:

```bash
python -m tools.lint.run --paths apps/api-gateway/src
```

## Notes

CI invokes the same commands via `make lint`, `make format`, and `make codegen` so local
results match pipeline behavior.
