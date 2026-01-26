# Local Dev Tools

## Purpose

Document the local dev tooling used to automate development and CI workflows.

## What's inside

- `tools/local-dev/dev_down.sh`: File asset used by this component.
- `tools/local-dev/dev_up.sh`: File asset used by this component.
- `tools/local-dev/docker-compose.override.example.yml`: YAML definition or configuration used by this component.

## How it's used

These tools are invoked by Make targets and CI pipelines.

## How to run / develop / test

Refer to the Makefile targets or run the module directly as needed.

## Configuration

Tooling configuration lives in repo-level config files and `.env` where applicable.

## Troubleshooting

- Command not found: ensure dev dependencies are installed (`make install-dev`).
- Tool errors: inspect logs and verify referenced paths exist.
