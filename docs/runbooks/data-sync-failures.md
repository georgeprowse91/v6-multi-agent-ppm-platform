# Data Sync Failures

## Purpose

Restore connector syncs when jobs back up, fail, or produce partial data.

## Scope

- Data Sync Service (`services/data-sync-service`)
- Connector runtimes (`connectors/*/src`)
- Data quality and lineage artifacts (`data/quality/`, `data/lineage/`)

## Symptoms

- `/sync/run` responses remain in `queued` or `planned` status.
- Connector-specific mappings are missing or invalid.
- Lineage artifacts are missing or contain redacted fields unexpectedly.

## Immediate checks

1. **Service health**
   ```bash
   curl -sS http://localhost:8080/healthz
   ```
2. **Inspect job status store**
   ```bash
   cat services/data-sync-service/storage/status.json
   ```
3. **Review configured rules**
   ```bash
   ls services/data-sync-service/rules
   ```

## Diagnostics

### 1) Validate connector configuration

- Confirm the connector is enabled in `config/connectors/integrations.yaml`.
- Ensure manifest and mapping files exist (e.g., `connectors/jira/manifest.yaml`).

### 2) Validate mappings

- Check mapping YAML targets against canonical schemas in `data/schemas/`.
- Run a dry-run mapping with the connector runtime (example for Jira):
  ```bash
  python -m connectors.jira.src.main connectors/jira/tests/fixtures/projects.json --tenant dev-tenant
  ```

### 3) Validate queue configuration

- If using Azure Service Bus, confirm `SERVICE_BUS_CONNECTION_STRING` and `SERVICE_BUS_QUEUE` are set.
- If not set, the service falls back to an in-memory queue (suitable only for local development).

### 4) Validate lineage masking

- Lineage payloads are masked by `packages/security` before returning status.
- Confirm masking rules in `packages/security/src/security/lineage.py` align with classification settings.

## Remediation steps

- **Missing mappings:** Create or update mapping YAMLs under `connectors/<name>/mappings/` and re-run the sync.
- **Queue misconfiguration:** Set Service Bus environment variables or use local mode for dev.
- **Invalid schema targets:** Update mapping targets to match `data/schemas/*.schema.json`.
- **Backlogged jobs:** Delete stale entries in `services/data-sync-service/storage/status.json` and re-trigger `/sync/run`.

## Verification

- Trigger a sync run:
  ```bash
  curl -sS -X POST http://localhost:8080/sync/run -H "Content-Type: application/json" -H "X-Tenant-ID: dev-tenant" -d '{"connector":"jira","dry_run":true}' | jq
  ```
- Confirm status updates:
  ```bash
  curl -sS http://localhost:8080/sync/status/<job_id> -H "X-Tenant-ID: dev-tenant" | jq
  ```

## Escalation

Escalate to the integration owner if:

- Mapping changes require schema updates.
- Connector auth credentials are invalid and require rotation.
- Service Bus connectivity is unstable or throttling.

## Related docs

- [Connector Overview](../connectors/overview.md)
- [Data Quality](../data/data-quality.md)
- [Data Lineage](../data/lineage.md)
