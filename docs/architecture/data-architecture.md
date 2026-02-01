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

## Persistence responsibilities

The platform exposes multiple storage backends so services can pick the store that matches the
data shape and access pattern. The matrix below summarizes how the current services use each
backend and where to look in the codebase for implementation details.

| Backend | Primary responsibility | Current usage in services |
| --- | --- | --- |
| PostgreSQL | Canonical, relational PPM entities that need schema validation, joins, and strong consistency. | Data service persists schema registry and canonical entities via its SQL store; orchestration state is configured to use Postgres for durability in production. |
| Cosmos DB | Flexible document storage for semi-structured records and large JSON payloads that benefit from partitioning by tenant or document type. | Integration persistence provides a Cosmos-backed document store (`CosmosDocumentStore`) that can be wired into services needing document-style storage. |
| Redis | Low-latency cache and transient state to avoid repeated queries against operational stores. | Cache provider in integration persistence supports Redis for shared caching and can be paired with cache-aside workflows. |

## Data flow patterns

- **Connector sync** updates canonical records and emits lineage.
- **Agent writes** validate against schemas and publish domain events.
- **Analytics pipeline** consumes events for reporting via the analytics service and KPI scheduler.

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

- **Implemented**: canonical schemas, lineage artifacts, quality rules, analytics service, and data-lineage service.
- **In progress**: expanded automated lineage generation across all connectors and analytics warehouse exports.

## Related docs

- [Data Model](../data/data-model.md)
- [Data Quality](../data/data-quality.md)
- [Data Lineage](../data/lineage.md)
