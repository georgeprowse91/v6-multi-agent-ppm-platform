# Connector Data Mapping

## Purpose

Describe how connector mappings translate source-system records into the platform’s canonical schemas.

## Mapping model

Each connector includes:

- A manifest (`connectors/<name>/manifest.yaml`) listing mappings and sync settings.
- Mapping files under `connectors/<name>/mappings/` describing field-level transformations.
- Runtime logic via the connector SDK (`connectors/sdk/src/runtime.py`).

## Mapping flow

1. **Load manifest:** Connector runtime loads and validates the manifest against `connectors/registry/schemas/connector-manifest.schema.json`.
2. **Load mapping specs:** Each mapping file defines `source`, `target`, and a list of field mappings.
3. **Apply mapping:** Records are transformed into canonical fields and enriched with `tenant_id`.

## Example mapping

```yaml
source: project
schema: project
target: project
fields:
  - source: id
    target: id
  - source: name
    target: name
```

Example file: `connectors/jira/mappings/project.yaml`.

## Validation guidance

- Ensure mapping targets exist in `data/schemas/*.schema.json`.
- Run mapping validation using connector fixtures.

Example dry-run with Jira fixtures:

```bash
python -m connectors.jira.src.main connectors/jira/tests/fixtures/projects.json --tenant dev-tenant
```

## Implementation status

- **Implemented:** Connector SDK runtime, manifest validation, mapping application.
- **Planned:** Advanced transformations (lookups, enums, date conversions) and quality scoring integration.

## Related docs

- [Connector Overview](overview.md)
- [Data Model](../data/data-model.md)
- [Connector SDK](../../connectors/sdk/README.md)
