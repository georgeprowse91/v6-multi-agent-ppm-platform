# Data Model, Quality & Lineage

## Purpose

Describe the canonical data model, quality scoring approach, and lineage artifacts that underpin the Multi-Agent PPM Platform.

## Architecture-level context

The data layer provides a shared schema for agents and connectors. Canonical schemas live in `data/schemas/`, quality rules in `data/quality/`, and lineage artifacts in `data/lineage/`. Together they ensure consistent, auditable data across portfolios, programs, projects, and work items.

## Key docs

- **Canonical data model** → [data-model.md](data-model.md)
- **Data quality rules** → [data-quality.md](data-quality.md)
- **Lineage capture** → [lineage.md](lineage.md)

## Usage example

Open the project schema:

```bash
sed -n '1,80p' data/schemas/project.schema.json
```

## How to verify

List available schemas:

```bash
ls data/schemas
```

Expected output: schema files for portfolio, program, project, and work items.

## Related docs

- [Data Architecture](../architecture/data-architecture.md)
- [Connector Overview](../connectors/overview.md)
