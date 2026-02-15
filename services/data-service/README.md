# Data Service

## Purpose

Centralize canonical entity storage and manage JSON Schema versions for the platform.

## Key endpoints

- [healthz](/GET /healthz): Service health check.
- [schemas](/POST /v1/schemas): Register a schema (auto-increments version when omitted).
- [schemas](/GET /v1/schemas): List schemas with latest versions.
- [versions](/GET /v1/schemas/{schema_name}/versions): List all versions for a schema.
- [latest](/GET /v1/schemas/{schema_name}/latest): Retrieve latest schema.
- [{schema_name}](/POST /entities/{schema_name}): Store a canonical entity after validation.
- [{entity_id}](/GET /entities/{schema_name}/{entity_id}): Retrieve a canonical entity.

**Default port:** `8080`

## Configuration

- `DATA_SERVICE_DATABASE_URL`: PostgreSQL connection string (falls back to `DATABASE_URL`).
- `DATA_SERVICE_LOAD_SEED_SCHEMAS`: Set to `false` to skip seeding `data/schemas` at startup.

## Local development

Run the service locally:

```bash
python services/data-service/main.py
```

Seed schemas from `data/schemas` by default; set `DATA_SERVICE_LOAD_SEED_SCHEMAS=false` to disable.
