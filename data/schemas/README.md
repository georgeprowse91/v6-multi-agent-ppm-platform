# Schemas

Canonical JSON schemas defining the structure of platform entities. Each schema follows the JSON Schema specification and has a corresponding example document.

## Directory structure

| Folder | Description |
|--------|-------------|
| [examples/](./examples/) | Example JSON documents for each schema |

## Key files

| File | Description |
|------|-------------|
| `project.schema.json` | Project entity schema |
| `portfolio.schema.json` | Portfolio entity schema |
| `program.schema.json` | Program entity schema |
| `demand.schema.json` | Demand entity schema |
| `resource.schema.json` | Resource entity schema |
| `work-item.schema.json` | Work item entity schema |
| `risk.schema.json` | Risk entity schema |
| `issue.schema.json` | Issue entity schema |
| `budget.schema.json` | Budget entity schema |
| `roi.schema.json` | ROI entity schema |
| `vendor.schema.json` | Vendor entity schema |
| `document.schema.json` | Document entity schema |
| `agent_config.schema.json` | Agent configuration schema |
| `audit-event.schema.json` | Audit event schema |

## Versioning and compatibility

Schemas can declare `x-schema-metadata` with semantic `version` and `compatibility_mode`. See `docs/schema-compatibility-matrix.md` for compatibility policy, CI enforcement, and migration CLI usage.
