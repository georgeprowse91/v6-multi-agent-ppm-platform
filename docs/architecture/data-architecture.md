# Data Architecture

## Purpose

Describe how canonical PPM data is stored, validated, synchronized, and audited across the platform.

## Architecture-level context

Data architecture ties together canonical schemas (`data/schemas/`), quality rules (`data/quality/`), lineage artifacts (`data/lineage/`), and the services that store and query the data. It enables agents and connectors to share a consistent view of portfolios, programs, projects, and work items.

## Storage layers

- **Operational store**: PostgreSQL for canonical entities.
- **Cache**: Redis for fast reads of frequently accessed data.
- **Document storage**: Blob storage for charters, contracts, and evidence files.
- **Event stream**: Service Bus for domain events and sync notifications.

## Data flow patterns

- **Connector sync** updates canonical records and emits lineage.
- **Agent writes** validate against schemas and publish domain events.
- **Analytics pipeline** consumes events for reporting (planned).

## Diagram

```text
PlantUML: docs/architecture/diagrams/data-lineage.puml
```

## Usage example

Inspect the canonical project schema:

```bash
sed -n '1,80p' data/schemas/project.schema.json
```

## How to verify

Confirm lineage artifacts are present:

```bash
ls data/lineage
```

Expected output: `example-lineage.json` and `README.md`.

## Implementation status

- **Implemented**: canonical schemas, example lineage artifacts, quality rules.
- **Planned**: automated lineage generation and analytics warehouse.

## Related docs

- [Data Model](../data/data-model.md)
- [Data Quality](../data/data-quality.md)
- [Data Lineage](../data/lineage.md)
