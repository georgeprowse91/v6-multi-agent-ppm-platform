# Backup and Recovery Runbook

Operational procedures for backup and recovery of the PPM platform data stores.

## Backup schedule and retention

| Data Store | Backup Frequency | Retention Period | Method |
|-----------|-----------------|-----------------|--------|
| Cosmos DB | Continuous | 30 days | Azure continuous backup |
| Blob Storage | Daily | 90 days | Azure Blob versioning + snapshots |
| Redis Cache | Every 6 hours | 7 days | RDB snapshots |
| Key Vault | Continuous | 90 days (soft delete) | Azure built-in |
| Configuration | Per commit | Indefinite | Git repository |

### Automated Backups

Backups are managed through Azure-native mechanisms:

1. Cosmos DB continuous backup with point-in-time restore.
2. Blob Storage soft delete and versioning enabled.
3. Redis RDB persistence with AOF for critical caches.

### Manual Backup Triggers

For ad-hoc backups before major changes:

```bash
# Export Cosmos DB collection
az cosmosdb collection export --name ppm-db --collection projects --output backup/

# Snapshot Blob Storage container
az storage blob snapshot --container-name ppm-documents --account-name ppmstorage
```

## Recovery procedures

### Cosmos DB Recovery

1. Identify the target restore point (timestamp).
2. Initiate point-in-time restore:
   ```bash
   az cosmosdb restore --account-name ppm-cosmos \
     --restore-timestamp "2026-03-06T00:00:00Z" \
     --target-database-account-name ppm-cosmos-restored
   ```
3. Validate restored data integrity.
4. Swap the connection string to point to the restored account.

### Blob Storage Recovery

1. List available blob versions or snapshots.
2. Restore the required version:
   ```bash
   az storage blob copy start --source-uri <snapshot-uri> --destination-blob <blob-name>
   ```

### Redis Recovery

1. Stop the application to prevent writes during recovery.
2. Restore from the latest RDB snapshot.
3. Restart Redis and verify data consistency.
4. Resume application traffic.

## Post-recovery validation checklist

After any recovery operation:

- [ ] Verify service health endpoints return OK.
- [ ] Run data integrity checks across all stores.
- [ ] Confirm agent operations function correctly.
- [ ] Validate connector sync state is consistent.
- [ ] Check audit log continuity.
- [ ] Notify stakeholders of recovery completion.
