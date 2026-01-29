# Data Lineage Service

## Purpose

Capture lineage events and compute data quality scores for analytics and auditing.

## Key endpoints

- `GET /healthz`: Service health check.
- `POST /lineage/events`: Ingest a lineage event and compute quality scores.
- `GET /lineage/events`: List lineage events for the tenant.
- `GET /lineage/events/{lineage_id}`: Retrieve a lineage event.
- `GET /lineage/graph`: Retrieve a lineage graph (nodes + edges).
- `GET /quality/summary`: Retrieve quality score summaries.

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
