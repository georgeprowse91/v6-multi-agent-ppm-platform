# Disaster Recovery

This runbook outlines DR planning, RTO/RPO targets, and recovery steps for the Multi-Agent PPM platform.

## Recovery Objectives

| Component | RTO | RPO | Notes |
| --- | --- | --- | --- |
| API Gateway + UI | 1 hour | 15 minutes | Stateless services behind load balancer. |
| Workflow Service | 2 hours | 30 minutes | Requires workflow state DB recovery. |
| Audit Log (WORM) | 4 hours | 0 minutes | Immutable storage with geo-redundancy. |
| Data Sync Service | 2 hours | 30 minutes | Resume from Service Bus checkpoints. |

## Preconditions

- Latest Terraform state available in remote backend.
- Backup snapshots for Postgres, Redis, and blob storage retained per policy.
- DR environment credentials stored in Azure Key Vault.

## Recovery Steps

1. **Declare DR event**
   - Notify on-call lead and incident commander.
   - Open DR ticket and record incident timeline.
2. **Assess impact**
   - Confirm region outage or data corruption scope.
   - Identify affected services and data domains.
3. **Restore infrastructure**
   - Apply Terraform in DR region using remote backend.
   - Validate Service Bus, Key Vault, and Storage Accounts.
4. **Restore databases**
   - Restore Postgres snapshot to DR instance.
   - Validate schema using `alembic upgrade head` if required.
5. **Restore workflow state**
   - Validate workflow service DB and resume pending workflows.
   - Replay audit events for in-flight workflows if needed.
6. **Rehydrate audit log**
   - Verify WORM container immutability policies.
   - Validate encryption keys and retention policies.
7. **Cutover traffic**
   - Update DNS or Traffic Manager to DR endpoints.
   - Monitor health checks and SLO dashboards.
8. **Post-recovery validation**
   - Run smoke tests and e2e workflows.
   - Confirm telemetry ingestion to Azure Monitor.
9. **Postmortem**
   - Document root cause, remediation, and follow-ups.

## Validation Checklist

- [ ] API gateway `/healthz` responds with `200`.
- [ ] Workflow engine can start and resume workflows.
- [ ] Audit log ingestion returns `202` and events are immutable.
- [ ] Telemetry pipeline exports to Azure Monitor.
- [ ] Data sync queue has backlog drained.

## DR Testing Procedures

Run a DR drill at least twice per year or after major infrastructure changes.

1. Provision a DR sandbox environment in the secondary region.
2. Restore the latest backups to the DR environment.
3. Execute smoke and e2e tests (`pytest tests/e2e`).
4. Validate SLAs under load (`pytest tests/load`).
5. Document outcomes, issues, and remediation tasks.
