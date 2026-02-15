# Codegen Tools

## Purpose

Document the codegen tooling used to automate development and CI workflows.

## What's inside

- [__init__.py](/tools/codegen/__init__.py): Python module used by this component.
- [codegen_config.yaml](/tools/codegen/codegen_config.yaml): YAML definition or configuration used by this component.
- [run.py](/tools/codegen/run.py): Python module used by this component.

## How it's used

These tools are invoked by Make targets and CI pipelines.

## How to run / develop / test

Refer to the Makefile targets or run the module directly as needed.

## Configuration

Tooling configuration lives in repo-level config files and `.env` where applicable.

## Troubleshooting

- Command not found: ensure dev dependencies are installed (`make install-dev`).
- Tool errors: inspect logs and verify referenced paths exist.
