# Workday Connector

Synchronizes HR and cost center data with Workday, supporting inbound project import and outbound dry-run mapping.

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
