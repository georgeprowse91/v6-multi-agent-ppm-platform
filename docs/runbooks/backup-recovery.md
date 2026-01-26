# Backup and Recovery Runbook

This runbook describes backup configuration, retention schedules, and recovery procedures for the Multi-Agent PPM platform.

## Scope

- **PostgreSQL** (primary transactional datastore)
- **Redis** (queue and cache data)
- **Audit Log WORM Storage**
- **Configuration and secrets** (Key Vault)

## Backup schedule and retention

| Component | Backup method | Frequency | Retention | Storage |
| --- | --- | --- | --- | --- |
| PostgreSQL | Azure Database for PostgreSQL automated backups | Continuous + nightly snapshots | 35 days | Geo-redundant storage (GRS) |
| Redis | Azure Redis persistence | Hourly | 7 days | Geo-redundant storage (GRS) |
| Audit Log | WORM storage with retention policies | Real-time ingestion | Per `config/retention/policies.yaml` | Immutable blob container |
| Kubernetes manifests | GitOps (repository) | Per release | Git history | GitHub |

## Pre-requisites

- Access to the Azure subscription and resource group.
- Azure Key Vault permissions to retrieve service credentials.
- Terraform backend configured for the target environment.

## Backup verification

1. **PostgreSQL**
   - Confirm backups exist in Azure Portal (Backups > Automated backups).
   - Ensure the latest snapshot is within the last 24 hours.
2. **Redis**
   - Validate persistence status via Redis configuration in Azure Portal.
   - Confirm backups are healthy with the last persistence time.
3. **Audit Log**
   - Validate WORM storage container immutability policy is enabled.
   - Run retention enforcement job and confirm no errors.

## Recovery procedures

### 1. PostgreSQL restore

1. Identify the latest valid backup in Azure Portal.
2. Restore to a new server (point-in-time restore).
3. Update service connection strings to use the restored instance.
4. Run database migrations:

```bash
alembic upgrade head
```

### 2. Redis restore

1. Restore the Redis cache from the latest persistence snapshot.
2. Validate connection health and keyspace population.
3. Restart dependent services (API Gateway, Data Sync Service).

### 3. Audit log restore

1. Validate the immutable blob container and encryption keys.
2. Verify audit retention metadata on sample records.
3. Re-run retention enforcement to remove expired entries.

### 4. Kubernetes recovery

1. Re-apply Terraform to ensure infrastructure is present.
2. Deploy Helm charts for all services.
3. Validate service health endpoints.

## Post-recovery validation checklist

- [ ] API Gateway `/healthz` responds with `200`.
- [ ] Workflow engine can resume workflows.
- [ ] Audit log events are immutable and retrievable.
- [ ] Data sync queues are draining.
- [ ] Analytics jobs can list manifests.

## Automation hooks

- **Retention enforcement:** `services/audit-log/src/retention_job.py`
- **Schema validation:** `scripts/validate-schemas.py`
- **Placeholder checks:** `scripts/check-placeholders.py`
