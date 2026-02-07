# Tools

## Overview

This directory contains development and CI automation tooling for the multi-agent PPM platform. Tools cover code generation, formatting, linting, load testing, and local development environment setup. They are invoked by Make targets and CI pipelines.

## Directory structure

| Folder | Description |
| --- | --- |
| [codegen/](./codegen/) | Code generation tools |
| [format/](./format/) | Code formatting tools |
| [lint/](./lint/) | Code linting tools |
| [load_testing/](./load_testing/) | Load testing runner |
| [local-dev/](./local-dev/) | Local development environment (docker-compose) |

## Key files

| File | Description |
| --- | --- |
| [agent_runner.py](./agent_runner.py) | Agent execution runner |
| [agent_runner_core.py](./agent_runner_core.py) | Core agent runner logic |
| [connector_runner.py](./connector_runner.py) | Connector execution runner |
| [component_runner.py](./component_runner.py) | Component execution runner |
| [runtime_paths.py](./runtime_paths.py) | Runtime path resolution utilities |
| [__init__.py](./__init__.py) | Python package initializer |

## How to run / develop / test

Refer to the Makefile targets or run the module directly as needed.

## Configuration

Tooling configuration lives in repo-level config files and `.env` where applicable.

## Troubleshooting

- Command not found: ensure dev dependencies are installed (`make install-dev`).
- Tool errors: inspect logs and verify referenced paths exist.
