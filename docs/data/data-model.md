# Canonical Data Model

## Purpose

Describe the canonical PPM entities, where their schemas live, and how agents and connectors use them.

## Architecture-level context

The platform uses a canonical schema layer to normalize data from multiple systems. Schemas are stored in `data/schemas/` and referenced by connectors, agents, and services to validate payloads and maintain lineage.

## Canonical entities (current)

| Entity | Schema file | Primary owner (agent/service) |
| --- | --- | --- |
| Audit event | `data/schemas/audit-event.schema.json` | Audit Log Service |
| Budget | `data/schemas/budget.schema.json` | Agent 12 – Financial Management |
| Demand | `data/schemas/demand.schema.json` | Agent 04 – Demand & Intake |
| Document | `data/schemas/document.schema.json` | Agent 19 – Knowledge & Document |
| Issue | `data/schemas/issue.schema.json` | Agent 15 – Risk & Issue Management |
| Portfolio | `data/schemas/portfolio.schema.json` | Agent 06 – Portfolio Strategy & Optimization |
| Program | `data/schemas/program.schema.json` | Agent 07 – Program Management |
| Project | `data/schemas/project.schema.json` | Agent 08 – Project Definition & Scope |
| Resource | `data/schemas/resource.schema.json` | Agent 11 – Resource & Capacity |
| Risk | `data/schemas/risk.schema.json` | Agent 15 – Risk & Issue Management |
| ROI | `data/schemas/roi.schema.json` | Agent 05 – Business Case & Investment |
| Vendor | `data/schemas/vendor.schema.json` | Agent 13 – Vendor & Procurement |
| Work item | `data/schemas/work-item.schema.json` | Agent 10 – Schedule & Planning |

## Example payload (Project)

```json
{
  "id": "PROJ-2026-001",
  "name": "ERP Modernization",
  "status": "in_progress",
  "portfolio_id": "PORT-001",
  "program_id": "PROG-2026-01",
  "owner_email": "pm@ppm.georgeprowse91.com",
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

- **Implemented:** Base schemas in `data/schemas/` and validation in the audit log service.
- **Planned:** Centralized schema registry APIs and schema version promotion workflows.

## Related docs

- [Data Architecture](../architecture/data-architecture.md)
- [Data Quality](data-quality.md)
- [Data Lineage](lineage.md)
