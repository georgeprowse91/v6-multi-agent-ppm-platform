# Data

> This section documents the canonical data layer of the Multi-Agent PPM platform: the entity model and schemas that all agents and connectors share, the quality scoring rules applied during sync, and the lineage tracing that provides end-to-end auditability from external systems through to canonical storage.

## Contents

- [Overview](#overview)
- [Data Model](#data-model)
- [Data Quality](#data-quality)
- [Data Lineage](#data-lineage)

---

## Overview

The platform uses a canonical schema layer to normalise data from multiple source systems. All schemas live under `data/schemas/` and are the authoritative definition of every entity. Connectors, agents, and services validate payloads against these schemas before persisting or propagating data.

Internal links across this documentation can be validated with:

```bash
python ops/scripts/check-links.py
```

If a diagram referenced in these docs cannot be found, verify that the file exists under `docs/architecture/diagrams/`.

---

## Data Model

The canonical data model describes every PPM entity, where its schema lives, and which agent or service owns it.

### Canonical entities

| Entity | Schema file | Primary owner |
| --- | --- | --- |
| Audit event | `data/schemas/audit-event.schema.json` | Audit Log Service |
| Budget | `data/schemas/budget.schema.json` | Financial Management agent |
| Demand | `data/schemas/demand.schema.json` | Demand Intake agent |
| Document | `data/schemas/document.schema.json` | Knowledge Management agent |
| Issue | `data/schemas/issue.schema.json` | Risk Management agent |
| Portfolio | `data/schemas/portfolio.schema.json` | Portfolio Optimisation agent |
| Program | `data/schemas/program.schema.json` | Program Management agent |
| Project | `data/schemas/project.schema.json` | Scope Definition agent |
| Resource | `data/schemas/resource.schema.json` | Resource Management agent |
| Risk | `data/schemas/risk.schema.json` | Risk Management agent |
| ROI | `data/schemas/roi.schema.json` | Business Case agent |
| Scenario | `data/schemas/scenario.schema.json` | Portfolio Optimisation agent |
| Vendor | `data/schemas/vendor.schema.json` | Vendor Procurement agent |
| Work item | `data/schemas/work-item.schema.json` | Schedule Planning agent |

### Platform schemas (runtime/infrastructure)

| Schema | Schema file | Owner |
| --- | --- | --- |
| Agent configuration | `data/schemas/agent_config.schema.json` | Agent Config Service |
| Agent run | `data/schemas/agent-run.schema.json` | Agent Runtime Service |

### Example payload (Project)

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
  "currency": "AUD"
}
```

List all schema files:

```bash
ls data/schemas
```

### Propagation rules and conflict handling

Canonical entities propagate updates between connectors, agents, and downstream consumers using explicit rules stored in the Data Sync Service.

**Propagation rules**

- **Directional propagation:** Updates flow from a declared source system to a target canonical entity.
- **Mode-aware application:**
  - `merge` — update only fields present in the incoming payload, preserving existing canonical values.
  - `replace` — overwrite the canonical payload with the incoming payload.
  - `enrich` — append non-null fields without overwriting existing canonical values.
- **Field-level constraints:** Only mapped target fields are eligible for propagation.
- **Lineage requirements:** Every propagated update emits lineage metadata with source, target, and transformation steps.

**Conflict handling strategies**

- `source_of_truth` — always accept updates from the declared source system.
- `last_write_wins` — compare `updated_at` timestamps; apply the newer update and skip stale payloads.
- `manual_required` — record conflicts for review when updates collide or policy requires human approval.
- **Audit trail** — conflicts are logged with source, target entity, timestamps, and strategy applied.

### Implementation status

- Base schemas in `data/schemas/` and payload validation in the Audit Log Service are implemented.
- Schema registry APIs with versioning and promotion workflows in the Data Service are implemented.

**Related:** Data Architecture · [Data Quality](#data-quality) · [Data Lineage](#data-lineage)

---

## Data Quality

Data quality scoring is executed by the Data Synchronisation agent. Rules are stored in `data/quality/rules.yaml` and applied to every incoming record before it is persisted. Scores are captured in lineage artifacts for auditability.

### Quality dimensions

- **Completeness** — required fields are present.
- **Validity** — values match expected formats or ranges.
- **Consistency** — values align with canonical enums and references.
- **Timeliness** — data freshness meets sync policy.

### Example rule

```yaml
- id: project-required-fields
  entity: project
  checks:
    - field: project.id
      type: required
```

Full rule set: `data/quality/rules.yaml`. View the first 120 lines:

```bash
sed -n '1,120p' data/quality/rules.yaml
```

Confirm the rule file exists:

```bash
ls data/quality/rules.yaml
```

### Implementation status

- Baseline rules and scoring weights are implemented.
- Automated remediation workflows with API-triggered fixes in the Lineage Service are implemented.

**Related:** [Data Model](#data-model) · [Data Lineage](#data-lineage)

---

## Data Lineage

Lineage provides end-to-end traceability from external systems into canonical schemas. Every connector sync and agent write emits a lineage event that is persisted in the `lineage_events` database table for audit, compliance, and analytics purposes.

### Capture approach

- **Trigger:** every connector sync or agent write.
- **Payload:** source system, record IDs, transformations applied, quality score.
- **Storage:** `lineage_events` database table (schema below).

### `lineage_events` table

| Column | Type | Notes |
| --- | --- | --- |
| `lineage_id` | text (PK) | Unique lineage event ID |
| `tenant_id` | text | Tenant scope |
| `connector_id` | text | Connector identifier |
| `work_item_id` | text (nullable) | Populated when target schema is `work-item` |
| `source_entity` | json | Source entity metadata |
| `target_entity` | json | Target entity metadata |
| `transformations` | json | Ordered list of transformation steps |
| `entity_type` | text (nullable) | Canonical entity type |
| `entity_payload` | json (nullable) | Canonical entity payload |
| `quality` | json (nullable) | Data quality metrics |
| `classification` | text | Classification label |
| `metadata` | json (nullable) | Additional metadata |
| `timestamp` | text | Sync timestamp (ISO 8601) |
| `retention_until` | text | Retention policy cutoff |

### Example lineage artifact

```json
{
  "id": "lin-2026-01-15-001",
  "connector": "jira",
  "source": {"system": "jira", "object": "project"},
  "target": {"schema": "project", "record_id": "PROJ-2026-001"}
}
```

Full example: `data/lineage/example-lineage.json`.

### Querying lineage

Query by work item ID via the API gateway:

```bash
curl -H "X-Tenant-ID: tenant-a" \
  "http://localhost:8000/v1/lineage?work_item_id=WI-100"
```

Query by connector ID via the API gateway:

```bash
curl -H "X-Tenant-ID: tenant-a" \
  "http://localhost:8000/v1/lineage?connector_id=jira"
```

Query directly from the database:

```sql
SELECT lineage_id, connector_id, work_item_id, timestamp
FROM lineage_events
WHERE connector_id = 'jira'
ORDER BY timestamp DESC;
```

### Implementation status

- Automated lineage generation, storage in `lineage_events`, and the query API are implemented.

**Related:** Connector Overview · [Data Quality](#data-quality)
