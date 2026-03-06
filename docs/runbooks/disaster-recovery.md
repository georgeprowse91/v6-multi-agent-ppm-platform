# Disaster Recovery Runbook

## DR Testing Procedures

This runbook documents the disaster recovery procedures for the PPM platform.

## Recovery Objectives

| Metric | Target |
|--------|--------|
| RTO (Recovery Time Objective) | 4 hours |
| RPO (Recovery Point Objective) | 1 hour |

## DR drill Schedule

DR drill exercises are conducted quarterly to validate recovery procedures.

### Pre-drill Checklist

1. Notify all stakeholders of the DR drill window.
2. Verify backup integrity for all critical data stores.
3. Confirm the secondary region infrastructure is provisioned.
4. Validate DNS failover configuration.

### DR drill Execution

1. Simulate primary region failure by redirecting traffic.
2. Activate the secondary region deployment:
   ```bash
   az traffic-manager profile update --name ppm-tm --resource-group ppm-rg --status Enabled
   ```
3. Verify all services are healthy in the secondary region.
4. Run smoke tests against the failover environment.
5. Validate data consistency between regions.

### Post-drill Review

1. Document recovery time achieved vs. RTO target.
2. Record any issues encountered during failover.
3. Update procedures based on lessons learned.
4. File the DR drill report with the compliance team.

## Database Recovery

1. Identify the latest consistent backup.
2. Restore from Azure Cosmos DB point-in-time recovery.
3. Verify data integrity after restoration.
4. Re-run any missed migrations if needed.

## Service Recovery Order

1. Identity & Access Service
2. Database / Data Service
3. API Gateway
4. Agent Runtime
5. Remaining services in parallel
