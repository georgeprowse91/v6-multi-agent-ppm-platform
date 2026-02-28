# Azure DevOps Connector

Synchronizes work items, projects, and boards between Azure DevOps and the platform (inbound and outbound).

## Directory structure

| Folder | Description |
| --- | --- |
| [src/](./src/) | Connector implementation |
| [mappings/](./mappings/) | Field mapping definitions |
| [tests/](./tests/) | Test suites and fixtures |

## Key files

- `manifest.yaml` — Connector manifest with metadata and sync configuration
- `Dockerfile` — Container build recipe
- `__init__.py` — Python package marker
