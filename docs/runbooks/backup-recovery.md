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

## Automated backups

- **Azure Database for PostgreSQL:** automated backups enabled with point-in-time restore and geo-redundant storage.
- **Redis:** persistence configured with scheduled snapshots.
- **Audit log:** continuous export to immutable storage with retention policies.
- **Validation automation:** `tests/test_backup_runbook.py` validates runbook requirements and retention policies.

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

#### Option A: Point-in-Time Restore (Preferred)

```bash
# List available restore points
az postgres flexible-server backup list \
  --resource-group ppm-production \
  --name ppm-postgresql

# Restore to a specific point in time
az postgres flexible-server restore \
  --resource-group ppm-production \
  --name ppm-postgresql-restored \
  --source-server ppm-postgresql \
  --restore-time "2024-01-15T10:00:00Z"

# Verify the restored server is ready
az postgres flexible-server show \
  --resource-group ppm-production \
  --name ppm-postgresql-restored \
  --query "state"
```

#### Option B: Geo-Restore (Disaster Recovery)

```bash
# Restore from geo-redundant backup to a different region
az postgres flexible-server geo-restore \
  --resource-group ppm-dr \
  --name ppm-postgresql-dr \
  --source-server /subscriptions/<sub-id>/resourceGroups/ppm-production/providers/Microsoft.DBforPostgreSQL/flexibleServers/ppm-postgresql \
  --location "West US 2"
```

#### Post-Restore Steps

1. Update connection string in Key Vault:
   ```bash
   az keyvault secret set \
     --vault-name ppm-keyvault \
     --name database-url \
     --value "postgresql://user:pass@ppm-postgresql-restored.postgres.database.azure.com:5432/ppm"
   ```

2. Run database migrations:
   ```bash
   alembic upgrade head
   ```

3. Restart services to pick up new connection:
   ```bash
   kubectl rollout restart deployment -n ppm-platform
   ```

4. Validate data integrity:
   ```bash
   python scripts/validate-data-integrity.py --full-scan
   ```

### 2. Redis restore

#### Option A: Restore from RDB Snapshot

```bash
# Check available snapshots
az redis export \
  --resource-group ppm-production \
  --name ppm-redis \
  --prefix backup \
  --container "https://ppmbackups.blob.core.windows.net/redis-backups"

# Import from snapshot
az redis import \
  --resource-group ppm-production \
  --name ppm-redis \
  --files "https://ppmbackups.blob.core.windows.net/redis-backups/backup.rdb"
```

#### Option B: Create New Redis Instance

If the Redis instance is corrupted, create a new one:

```bash
# Create new Redis instance
az redis create \
  --resource-group ppm-production \
  --name ppm-redis-new \
  --location "East US" \
  --sku Premium \
  --vm-size P1

# Update connection string in Key Vault
az keyvault secret set \
  --vault-name ppm-keyvault \
  --name redis-url \
  --value "rediss://ppm-redis-new.redis.cache.windows.net:6380?password=<access-key>"
```

#### Post-Restore Validation

```bash
# Test Redis connectivity
redis-cli -h ppm-redis.redis.cache.windows.net -p 6380 -a <password> --tls ping

# Check keyspace info
redis-cli -h ppm-redis.redis.cache.windows.net -p 6380 -a <password> --tls info keyspace
```

Restart dependent services:
```bash
kubectl rollout restart deployment/ppm-api -n ppm-platform
kubectl rollout restart deployment/ppm-data-sync -n ppm-platform
```

### 3. Audit log restore

Audit logs are stored in WORM (Write Once Read Many) immutable storage and cannot be modified or deleted until the retention period expires.

#### Verify Immutability

```bash
# Check immutability policy
az storage container immutability-policy show \
  --account-name ppmauditlogs \
  --container-name audit-worm

# List audit log blobs
az storage blob list \
  --account-name ppmauditlogs \
  --container-name audit-worm \
  --query "[].{name:name, lastModified:properties.lastModified}" \
  --output table
```

#### Restore Access to Audit Logs

If audit log service cannot access storage:

1. Verify managed identity permissions:
   ```bash
   az role assignment list \
     --assignee <managed-identity-object-id> \
     --scope /subscriptions/<sub-id>/resourceGroups/ppm-production/providers/Microsoft.Storage/storageAccounts/ppmauditlogs
   ```

2. Re-grant access if needed:
   ```bash
   az role assignment create \
     --role "Storage Blob Data Reader" \
     --assignee <managed-identity-object-id> \
     --scope /subscriptions/<sub-id>/resourceGroups/ppm-production/providers/Microsoft.Storage/storageAccounts/ppmauditlogs
   ```

3. Verify encryption keys in Key Vault are accessible.

### 4. Kubernetes recovery

#### Full Cluster Recovery

```bash
# Re-apply Terraform infrastructure
cd infra/terraform
terraform init
terraform plan -out=recovery.tfplan
terraform apply recovery.tfplan

# Verify AKS cluster is ready
az aks show \
  --resource-group ppm-production \
  --name ppm-aks \
  --query "provisioningState"

# Get credentials
az aks get-credentials \
  --resource-group ppm-production \
  --name ppm-aks \
  --overwrite-existing
```

#### Deploy Services

```bash
# Apply namespace and security policies
kubectl apply -f infra/kubernetes/manifests/

# Deploy platform services using Helm
helm dependency update infra/kubernetes/helm-charts/ppm-platform
helm upgrade --install ppm-platform infra/kubernetes/helm-charts/ppm-platform \
  --namespace ppm-platform \
  --create-namespace \
  -f infra/kubernetes/helm-charts/ppm-platform/values-production.yaml

# Verify all pods are running
kubectl get pods -n ppm-platform
kubectl wait --for=condition=ready pod -l app=ppm-api -n ppm-platform --timeout=300s
```

### 5. Complete disaster recovery

For a complete site failure, follow this order:

1. **Infrastructure**: Apply Terraform to recreate all Azure resources
2. **Database**: Geo-restore PostgreSQL from secondary region
3. **Redis**: Create new instance (cache data will rebuild)
4. **Secrets**: Restore Key Vault from backup or recreate secrets
5. **Kubernetes**: Deploy all services
6. **DNS**: Update DNS to point to new endpoints
7. **Validation**: Run full system validation

```bash
# Full DR recovery script
./scripts/disaster-recovery.sh --region "West US 2" --env production
```

## Post-recovery validation checklist

### Critical Services
- [ ] API Gateway `/healthz` responds with `200`
- [ ] API Gateway `/v1/health/ready` responds with `200`
- [ ] Workflow engine can resume workflows
- [ ] Orchestration service accepts new requests

### Data Layer
- [ ] PostgreSQL connections successful from all services
- [ ] Database migrations are current (`alembic current`)
- [ ] Project records can read/write the `benefits_realisation_plan` field
- [ ] Project records can read/write the `regulatory_category` field (`low|medium|high`)
- [ ] Redis connectivity verified
- [ ] Data sync queues are draining

### Security & Compliance
- [ ] Authentication flow working (test login)
- [ ] RBAC permissions enforced correctly
- [ ] Audit log events are immutable and retrievable
- [ ] Tenant isolation verified

### Integration
- [ ] Connector sync jobs executing
- [ ] Webhook notifications firing
- [ ] Analytics jobs can list manifests

### Performance
- [ ] Response times within SLA
- [ ] No elevated error rates
- [ ] HPA scaling correctly

## Backup testing schedule

| Test Type | Frequency | Owner | Last Tested |
| --- | --- | --- | --- |
| PostgreSQL PITR restore | Quarterly | Platform Team | - |
| Redis snapshot restore | Quarterly | Platform Team | - |
| Full DR failover | Annually | Platform + SRE | - |
| Audit log access verification | Monthly | Compliance | - |

## Automation hooks

- **Retention enforcement:** `services/audit-log/src/retention_job.py`
- **Schema validation:** `scripts/validate-schemas.py`
- **Placeholder checks:** `scripts/check-placeholders.py`
- **Data integrity validation:** `scripts/validate-data-integrity.py`
- **Disaster recovery:** `scripts/disaster-recovery.sh`
- **Backup verification:** `tests/test_backup_runbook.py`
