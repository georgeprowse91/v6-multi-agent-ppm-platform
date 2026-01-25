# Canonical Data Model

## Purpose

Describe the canonical PPM entities, where their schemas live, and how agents and connectors use them.

## Architecture-level context

The platform uses a canonical schema layer to normalize data from multiple systems. Schemas are stored in `data/schemas/` and referenced by connectors and agents to validate payloads and maintain lineage.

## Canonical entities (current)

| Entity | Schema file | Primary owner (agent) |
| --- | --- | --- |
| Portfolio | `data/schemas/portfolio.schema.json` | Portfolio Strategy (Agent 06) |
| Program | `data/schemas/program.schema.json` | Program Management (Agent 07) |
| Project | `data/schemas/project.schema.json` | Project Definition (Agent 08) |
| Work item | `data/schemas/work-item.schema.json` | Schedule & Planning (Agent 10) |
| Risk | `data/schemas/risk.schema.json` | Risk & Issue (Agent 15) |
| Issue | `data/schemas/issue.schema.json` | Risk & Issue (Agent 15) |
| Budget | `data/schemas/budget.schema.json` | Financial Management (Agent 12) |
| Vendor | `data/schemas/vendor.schema.json` | Vendor & Procurement (Agent 13) |

## Example payload (Project)

```json
{
  "id": "PROJ-2026-001",
  "name": "ERP Modernization",
  "status": "in_progress",
  "portfolio_id": "PORT-001",
  "program_id": "PROG-2026-01",
  "owner_email": "pm@example.com",
  "start_date": "2026-01-15",
  "end_date": "2026-12-20",
  "currency": "USD"
}
```

## Usage example

Open the project schema:

```bash
sed -n '1,80p' data/schemas/project.schema.json
```

## How to verify

List schema files:

```bash
ls data/schemas
```

Expected output: canonical schema JSON files.

## Implementation status

- **Implemented**: base schemas in `data/schemas/`.
- **Planned**: validation services and schema versioning tooling.

## Related docs

- [Data Architecture](../architecture/data-architecture.md)
- [Data Quality](data-quality.md)
- [Data Lineage](lineage.md)
