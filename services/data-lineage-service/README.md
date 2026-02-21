# Data Lineage Service

## Purpose

Capture lineage events and compute data quality scores for analytics and auditing.

## Key endpoints

- [healthz](/GET /healthz): Service health check.
- [events](/POST /v1/lineage/events): Ingest a lineage event and compute quality scores.
- [events](/GET /v1/lineage/events): List lineage events for the tenant.
- [{lineage_id}](/GET /v1/lineage/events/{lineage_id}): Retrieve a lineage event.
- [graph](/GET /v1/lineage/graph): Retrieve a lineage graph (nodes + edges).
- [summary](/GET /v1/quality/summary): Retrieve quality score summaries.

**Default port:** `8080`

## Configuration

- `DATA_LINEAGE_STORE_PATH`: Local JSON store path (defaults to `services/data-lineage-service/storage/lineage.json`).
- `DATA_LINEAGE_RETENTION_POLICIES`: Optional path to retention policy YAML (defaults to `config/retention/policies.yaml`).
- `DATA_LINEAGE_CLASSIFICATION_LEVELS`: Optional path to classification YAML (defaults to `config/data-classification/levels.yaml`).

## Local development

Run the service locally:

```bash
python services/data-lineage-service/main.py
```

## Generated docs

- Endpoint reference (source of truth): [`docs/generated/services/data-lineage-service.md`](../../docs/generated/services/data-lineage-service.md).
- Regenerate with: `python ops/tools/codegen/generate_docs.py`.

## Ownership and support

- Owner: Platform Engineering
- Support: #ppm-platform-support

