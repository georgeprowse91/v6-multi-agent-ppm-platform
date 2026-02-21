# Codegen Tools

## Purpose

Generate and validate code-derived documentation artifacts used by CI.

## What's inside

- [__init__.py](./__init__.py): Python module marker.
- [codegen_config.yaml](./codegen_config.yaml): OpenAPI summary generation config.
- [run.py](./run.py): OpenAPI summary generator.
- [generate_docs.py](./generate_docs.py): Generated docs pipeline for service endpoints and connector capabilities.

## How it's used

- `python ops/tools/codegen/generate_docs.py` regenerates:
  - `docs/generated/services/*.md` from FastAPI route decorators.
  - `docs/connectors/generated/capability-matrix.md` and `maturity-inventory.json` from connector manifests + maturity inventory output.
- CI runs `make check-generated-docs` and fails on drift.

## How to run / develop / test

```bash
python ops/tools/codegen/generate_docs.py
make check-generated-docs
```
