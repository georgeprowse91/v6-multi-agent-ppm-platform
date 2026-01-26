# Tools

## Purpose

Document the tooling used to automate development and CI workflows.

## What's inside

- `tools/codegen`: Subdirectory containing codegen assets for this area.
- `tools/format`: Subdirectory containing format assets for this area.
- `tools/lint`: Subdirectory containing lint assets for this area.
- `tools/load_testing`: Subdirectory containing load testing assets for this area.
- `tools/local-dev`: Subdirectory containing local dev assets for this area.
- `tools/__init__.py`: Python module used by this component.

## How it's used

These tools are invoked by Make targets and CI pipelines.

## How to run / develop / test

Refer to the Makefile targets or run the module directly as needed.

## Configuration

Tooling configuration lives in repo-level config files and `.env` where applicable.

## Troubleshooting

- Command not found: ensure dev dependencies are installed (`make install-dev`).
- Tool errors: inspect logs and verify referenced paths exist.
