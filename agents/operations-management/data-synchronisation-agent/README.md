# Data Synchronisation Quality Specification

## Purpose

Define the responsibilities, workflows, and integration points for Data Synchronisation Quality. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- [src](/agents/operations-management/data-synchronisation-agent/src): Implementation source for this component.
- [tests](/agents/operations-management/data-synchronisation-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/operations-management/data-synchronisation-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## Scope, responsibilities, and decisioning

### Intended scope

- Govern data synchronization quality for mastered PPM entities (project, resource, vendor, financial, etc.) flowing between source systems and the canonical model.
- Validate inbound payloads, map them to canonical schemas, and enforce data-quality thresholds before propagation.
- Detect duplicates/conflicts and resolve or queue them based on configured policies.
- Emit audit, lineage, and telemetry events for downstream analytics and monitoring.

### Inputs

- **Action payloads** (via agent runner): `sync_data`, `run_sync`, `validate_data`, `detect_conflicts`, `resolve_conflict`, `detect_duplicates`, `merge_duplicates`, `get_quality_report`, `get_retry_queue`, `process_retries`, `reprocess_retry`, `get_dashboard`.
- **Configuration files** loaded at startup:
  - `config/data-synchronisation-agent/validation_rules.yaml`
  - `config/data-synchronisation-agent/pipelines.yaml`
  - `config/data-synchronisation-agent/schema_registry.yaml`
  - `config/data-synchronisation-agent/mapping_rules.yaml`
  - `config/data-synchronisation-agent/quality_thresholds.yaml`
- **External connectors**: Planview, SAP, Jira, Workday (via Key Vault + connector secrets).
- **Events**: `sync.start`, `sync.complete`, `conflict.detected` via Service Bus/Event Grid.

### Outputs

- **Canonical master records** persisted to state storage and optional databases.
- **Sync telemetry**: latency metrics, quality metrics, retry queue entries.
- **Quality reports**: per-entity summaries of completeness, consistency, timeliness.
- **Audit/lineage events** emitted to event bus, Log Analytics, and audit stores.

### Decision responsibilities

- **Data quality gating**: accept, reject, or retry a payload based on validation rules and quality thresholds.
- **Conflict strategy**: apply `last_write_wins`, `timestamp_based`, `authoritative_source`, `prefer_existing`, or `manual`.
- **Duplicate handling**: flag, merge, or reject based on fuzzy match confidence thresholds.
- **Retry policy**: determine retry eligibility and backoff based on failure reason and max attempts.

### Must / must-not behaviors

**Must**
- Enforce schema validation and rule-based validation before master record updates.
- Record sync logs, quality metrics, and audit events for every sync request.
- Preserve lineage and trace IDs for downstream observability.
- Queue failed validations for retry rather than silent drop.

**Must not**
- Must not overwrite authoritative fields when the source system is not the authority.
- Must not emit analytics insights (delegated to analytics agents) beyond raw metrics.
- Must not mutate canonical records without a successful validation pass.

## Overlap, leakage, and handoff boundaries

### Analytics agent (The Analytics Insights agent)

- **Overlap risk**: analytics reporting aggregates quality metrics; the Data Synchronisation agent produces the raw data quality signals and reports only.
- **Handoff boundary**: the Data Synchronisation agent publishes quality events/metrics; the Analytics Insights agent consumes, aggregates, and generates dashboards, KPIs, narratives, and forecasting.
- **Leakage to avoid**: the Data Synchronisation agent should not compute portfolio-level KPIs, forecasts, or narrative summaries.

### Approval Workflow agent

- **Overlap risk**: the Approval Workflow agent can orchestrate retries/compensation workflows. the Data Synchronisation agent owns data sync quality decisions and retry eligibility.
- **Handoff boundary**: the Data Synchronisation agent emits `sync.complete` and `conflict.detected` events and publishes retry queue status; the Approval Workflow agent uses these signals to trigger workflows (e.g., human review for manual conflict resolution).
- **Leakage to avoid**: the Data Synchronisation agent should not orchestrate complex multi-step workflow routing; defer to the Approval Workflow agent for orchestration.

## Functional gaps, inconsistencies, and alignment needs

- **Prompt/tool alignment**: ensure agent runner routes `get_quality_report`, `get_dashboard`, and retry actions to the Data Synchronisation agent instead of analytics agents.
- **Template alignment**: add/confirm templates for quality exception review workflows in the Approval Workflow agent and dashboards in analytics agents.
- **Connector alignment**: confirm connector credential availability in Key Vault for Planview/SAP/Jira/Workday and ensure sync mappings exist in `mapping_rules.yaml`.
- **UI alignment**: dashboards should visualize quality dimensions (completeness, consistency, timeliness) and include retry queue counts and conflict backlog.
- **Schema versioning**: ensure `schema_registry.yaml` and registered schemas include version metadata to avoid mismatched validation.

## Data quality rules (checkpoint-ready)

Minimum rules and thresholds for execution readiness:

1. **Completeness**: required fields present per schema + validation rules.
2. **Consistency**: field ranges and referential checks pass; no conflicting authoritative updates.
3. **Timeliness**: `updated_at` within SLA (`sync_latency_sla_seconds`, default 60s).
4. **Uniqueness**: duplicate detection confidence below `duplicate_confidence_threshold` (default 0.85).
5. **Schema compliance**: JSON schema validation passes for entity type.
6. **Auditability**: sync logs, lineage payload, and audit events recorded for every sync.

## Dependency map entry (checkpoint-ready)

**Upstream dependencies**
- Source systems: Planview, SAP, Jira, Workday.
- Schema and rule configs: `config/data-synchronisation-agent/*.yaml`.
- Event bus: Azure Service Bus / Event Grid.

**Downstream dependencies**
- Analytics agent (The Analytics Insights agent): quality metrics, reports, and sync telemetry.
- Approval Workflow agent: conflict and retry orchestration.
- Data stores: SQL/Cosmos for master records and audit history.

**Key events**
- `sync.start`, `sync.complete`, `conflict.detected`.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name data-synchronisation-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/data-synchronisation-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Required environment variables

Set the following variables to enable full integration:

**Azure Service Bus / Event Grid**
- `AZURE_SERVICE_BUS_CONNECTION_STRING`
- `AZURE_SERVICE_BUS_TOPIC_NAME` (optional, defaults to `ppm-events`)
- `AZURE_SERVICE_BUS_QUEUE_NAME` (optional, defaults to `ppm-sync-queue`)
- `EVENT_GRID_ENDPOINT`
- `EVENT_GRID_KEY`

**Azure Data Stores**
- `SQL_CONNECTION_STRING`
- `COSMOS_ENDPOINT`
- `COSMOS_KEY`

**Azure Data Factory & Functions**
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_DATA_FACTORY_NAME`
- `AZURE_FUNCTION_BASE_URL` (Function App base URL for ETL/transformations)
- `AZURE_FUNCTION_KEY` (optional, function key for secured endpoints)
- `AZURE_KEY_VAULT_URL`

**Azure Monitor / Log Analytics**
- `LOG_ANALYTICS_ENDPOINT`
- `LOG_ANALYTICS_RULE_ID`
- `LOG_ANALYTICS_STREAM_NAME` (optional, defaults to `DataSyncLatency`)

**Connector Credentials (stored in Azure Key Vault or set locally)**
- `PLANVIEW_CLIENT_ID`, `PLANVIEW_CLIENT_SECRET`, `PLANVIEW_REFRESH_TOKEN`, `PLANVIEW_INSTANCE_URL`
- `SAP_USERNAME`, `SAP_PASSWORD`, `SAP_URL`
- `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_INSTANCE_URL`
- `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`, `WORKDAY_API_URL`

### Local development

1. Copy `ops/config/.env.example` to `.env` and populate the required variables above.
2. Ensure the validation rules and pipeline configuration files exist:
   - `config/data-synchronisation-agent/validation_rules.yaml`
   - `config/data-synchronisation-agent/pipelines.yaml`
   - `config/data-synchronisation-agent/schema_registry.yaml`
   - `config/data-synchronisation-agent/mapping_rules.yaml`
   - `config/data-synchronisation-agent/quality_thresholds.yaml`
3. If you want to invoke Azure Functions locally, expose the Function App base URL and key in `.env`.
4. Run the agent locally:

```bash
python -m tools.agent_runner run-agent --name data-synchronisation-agent --dry-run
```

### Production deployment

1. Provision Azure Service Bus, Event Grid, Data Factory, SQL Database, Cosmos DB, and Log Analytics.
2. Store connector secrets in Azure Key Vault and grant the agent identity access to the vault.
3. Provide the environment variables above through your runtime (Kubernetes secrets, App Service settings, or managed identity configuration).
4. Deploy with the provided Dockerfile or orchestration tooling in `ops/infra/`.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.

## Events emitted

The agent publishes the following Service Bus events during synchronization:

- `sync.start` when a synchronization begins
- `sync.complete` on success, failure, or duplicate detection
- `conflict.detected` when update conflicts are recorded
