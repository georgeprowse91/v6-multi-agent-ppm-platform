## Data Sync Failures

Restore connector syncs when jobs back up, fail, or produce partial data.

### Scope

- Data Sync Service (`services/data-sync-service`)
- Connector runtimes (`connectors/*/src`)
- Data quality and lineage artifacts (`data/quality/`, `data/lineage/`)

### Symptoms

- `/v1/sync/run` responses remain in `queued` or `planned` status.
- Connector-specific mappings are missing or invalid.
- Lineage artifacts are missing or contain redacted fields unexpectedly.

### Immediate checks

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

### Diagnostics

#### 1) Validate connector configuration

- Confirm the connector is enabled in `ops/config/connectors/integrations.yaml`.
- Ensure manifest and mapping files exist (e.g., `connectors/jira/manifest.yaml`).

#### 2) Validate mappings

- Check mapping YAML targets against canonical schemas in `data/schemas/`.
- Run a dry-run mapping with the connector runtime (example for Jira):
  ```bash
  python -m integrations.connectors.jira.src.main connectors/jira/tests/fixtures/projects.json --tenant dev-tenant
  ```

#### 3) Validate queue configuration

- If using Azure Service Bus, confirm `SERVICE_BUS_CONNECTION_STRING` and `SERVICE_BUS_QUEUE` are set.
- If not set, the service falls back to an in-memory queue (suitable only for local development).

#### 4) Validate lineage masking

- Lineage payloads are masked by `packages/security` before returning status.
- Confirm masking rules in `packages/security/src/security/lineage.py` align with classification settings.

### Remediation steps

- **Missing mappings:** Create or update mapping YAMLs under `connectors/<name>/mappings/` and re-run the sync.
- **Queue misconfiguration:** Set Service Bus environment variables or use local mode for development.
- **Invalid schema targets:** Update mapping targets to match `data/schemas/*.schema.json`.
- **Backlogged jobs:** Delete stale entries in `services/data-sync-service/storage/status.json` and re-trigger `/v1/sync/run`.

### Verification

- Trigger a sync run:
  ```bash
  curl -sS -X POST http://localhost:8080/v1/sync/run \
    -H "Content-Type: application/json" \
    -H "X-Tenant-ID: dev-tenant" \
    -d '{"connector":"jira","dry_run":true}' | jq
  ```
- Confirm status updates:
  ```bash
  curl -sS http://localhost:8080/v1/sync/status/<job_id> -H "X-Tenant-ID: dev-tenant" | jq
  ```

### Escalation

Escalate to the integration owner if:

- Mapping changes require schema updates.
- Connector auth credentials are invalid and require rotation.
- Service Bus connectivity is unstable or throttling.

### Related docs

- [Connector Overview](../connectors/overview.md)
- [Data Quality](../data/data-quality.md)
- [Data Lineage](../data/lineage.md)

---

## Backup and Recovery

This section describes backup configuration, retention schedules, and recovery procedures for the Multi-Agent PPM platform.

### Scope

- **PostgreSQL** (primary transactional datastore)
- **Redis** (queue and cache data)
- **Audit Log WORM Storage**
- **Configuration and secrets** (Key Vault)

### Backup schedule and retention

| Component | Backup method | Frequency | Retention | Storage |
| --- | --- | --- | --- | --- |
| PostgreSQL | Azure Database for PostgreSQL automated backups | Continuous + nightly snapshots | 35 days | Geo-redundant storage (GRS) |
| Redis | Azure Redis persistence | Hourly | 7 days | Geo-redundant storage (GRS) |
| Audit Log | WORM storage with retention policies | Real-time ingestion | Per `ops/config/retention/policies.yaml` | Immutable blob container |
| Kubernetes manifests | GitOps (repository) | Per release | Git history | GitHub |

### Automated backups

- **Azure Database for PostgreSQL:** automated backups enabled with point-in-time restore and geo-redundant storage.
- **Redis:** persistence configured with scheduled snapshots.
- **Audit log:** continuous export to immutable storage with retention policies.
- **Validation automation:** `tests/test_backup_runbook.py` validates runbook requirements and retention policies.

### Pre-requisites

- Access to the Azure subscription and resource group.
- Azure Key Vault permissions to retrieve service credentials.
- Terraform backend configured for the target environment.

### Backup verification

1. **PostgreSQL**
   - Confirm backups exist in Azure Portal (Backups > Automated backups).
   - Ensure the latest snapshot is within the last 24 hours.
2. **Redis**
   - Validate persistence status via Redis configuration in Azure Portal.
   - Confirm backups are healthy with the last persistence time.
3. **Audit Log**
   - Validate WORM storage container immutability policy is enabled.
   - Run retention enforcement job and confirm no errors.

### Recovery procedures

#### 1. PostgreSQL restore

##### Option A: Point-in-Time Restore (Preferred)

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

##### Option B: Geo-Restore (Disaster Recovery)

```bash
# Restore from geo-redundant backup to a different region
az postgres flexible-server geo-restore \
  --resource-group ppm-dr \
  --name ppm-postgresql-dr \
  --source-server /subscriptions/<sub-id>/resourceGroups/ppm-production/providers/Microsoft.DBforPostgreSQL/flexibleServers/ppm-postgresql \
  --location "West US 2"
```

##### Post-Restore Steps

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

3. Restart services to pick up the new connection:
   ```bash
   kubectl rollout restart deployment -n ppm-platform
   ```

4. Validate data integrity:
   ```bash
   python ops/scripts/validate-data-integrity.py --full-scan
   ```

#### 2. Redis restore

##### Option A: Restore from RDB Snapshot

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

##### Option B: Create New Redis Instance

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

##### Post-Restore Validation

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

#### 3. Audit log restore

Audit logs are stored in WORM (Write Once Read Many) immutable storage and cannot be modified or deleted until the retention period expires.

##### Verify Immutability

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

##### Restore Access to Audit Logs

If the audit log service cannot access storage:

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

#### 4. Kubernetes recovery

##### Full Cluster Recovery

```bash
# Re-apply Terraform infrastructure
cd ops/infra/terraform
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

##### Deploy Services

```bash
# Apply namespace and security policies
kubectl apply -f ops/infra/kubernetes/manifests/

# Deploy platform services using Helm
helm dependency update ops/infra/kubernetes/helm-charts/ppm-platform
helm upgrade --install ppm-platform ops/infra/kubernetes/helm-charts/ppm-platform \
  --namespace ppm-platform \
  --create-namespace \
  -f ops/infra/kubernetes/helm-charts/ppm-platform/values-production.yaml

# Verify all pods are running
kubectl get pods -n ppm-platform
kubectl wait --for=condition=ready pod -l app=ppm-api -n ppm-platform --timeout=300s
```

#### 5. Complete disaster recovery

For a complete site failure, restore components in this order:

1. **Infrastructure**: Apply Terraform to recreate all Azure resources.
2. **Database**: Geo-restore PostgreSQL from the secondary region.
3. **Redis**: Create a new instance (cache data will rebuild automatically).
4. **Secrets**: Restore Key Vault from backup or recreate secrets.
5. **Kubernetes**: Deploy all services.
6. **DNS**: Update DNS to point to new endpoints.
7. **Validation**: Run full system validation.

```bash
# Full DR recovery script
./ops/scripts/disaster-recovery.sh --region "West US 2" --env production
```

### Post-recovery validation checklist

#### Critical Services
- [ ] API Gateway `/healthz` responds with `200`
- [ ] API Gateway `/v1/health/ready` responds with `200`
- [ ] Workflow engine can resume workflows
- [ ] Orchestration service accepts new requests

#### Data Layer
- [ ] PostgreSQL connections successful from all services
- [ ] Database migrations are current (`alembic current`)
- [ ] Project records can read/write the `benefits_realisation_plan` field
- [ ] Project records can read/write the `regulatory_category` field (`low|medium|high`)
- [ ] Redis connectivity verified
- [ ] Data sync queues are draining

#### Security and Compliance
- [ ] Authentication flow working (test login)
- [ ] RBAC permissions enforced correctly
- [ ] Audit log events are immutable and retrievable
- [ ] Tenant isolation verified

#### Integration
- [ ] Connector sync jobs executing
- [ ] Webhook notifications firing
- [ ] Analytics jobs can list manifests

#### Performance
- [ ] Response times within SLA
- [ ] No elevated error rates
- [ ] HPA scaling correctly

### Backup testing schedule

| Test Type | Frequency | Owner | Last Tested |
| --- | --- | --- | --- |
| PostgreSQL PITR restore | Quarterly | Platform Team | - |
| Redis snapshot restore | Quarterly | Platform Team | - |
| Full DR failover | Annually | Platform + SRE | - |
| Audit log access verification | Monthly | Compliance | - |

### Automation hooks

- **Retention enforcement:** `services/audit-log/src/retention_job.py`
- **Schema validation:** `ops/scripts/validate-schemas.py`
- **Placeholder checks:** `ops/scripts/check-placeholders.py`
- **Data integrity validation:** `ops/scripts/validate-data-integrity.py`
- **Disaster recovery:** `ops/scripts/disaster-recovery.sh`
- **Backup verification:** `tests/test_backup_runbook.py`

---

## Disaster Recovery

This section outlines DR planning, RTO/RPO targets, and recovery steps for the Multi-Agent PPM platform.

### Recovery objectives

| Component | RTO | RPO | Notes |
| --- | --- | --- | --- |
| API Gateway + UI | 1 hour | 15 minutes | Stateless services behind load balancer. |
| Workflow Service | 2 hours | 30 minutes | Requires workflow state DB recovery. |
| Audit Log (WORM) | 4 hours | 0 minutes | Immutable storage with geo-redundancy. |
| Data Sync Service | 2 hours | 30 minutes | Resume from Service Bus checkpoints. |

### Preconditions

- Latest Terraform state available in remote backend.
- Backup snapshots for Postgres, Redis, and blob storage retained per policy.
- DR environment credentials stored in Azure Key Vault.

### Recovery steps

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
   - Run smoke tests and end-to-end workflows.
   - Confirm telemetry ingestion to Azure Monitor.
9. **Postmortem**
   - Document root cause, remediation steps, and follow-up actions.

### Validation checklist

- [ ] API gateway `/healthz` responds with `200`.
- [ ] Workflow engine can start and resume workflows.
- [ ] Audit log ingestion returns `202` and events are immutable.
- [ ] Telemetry pipeline exports to Azure Monitor.
- [ ] Data sync queue backlog has drained.

### DR testing procedures

Run a DR drill at least twice per year or after major infrastructure changes.

1. Provision a DR sandbox environment in the secondary region.
2. Restore the latest backups to the DR environment.
3. Execute smoke and end-to-end tests (`pytest tests/e2e`).
4. Validate SLAs under load (`pytest tests/load`).
5. Document outcomes, issues, and remediation tasks.

---

## Secret Initialisation

This section documents how to bootstrap secrets for new environments.

### Scope

- Azure Key Vault secrets
- Kubernetes SecretProviderClass configuration
- Service principal credentials for CI/CD

### Initial bootstrap

1. **Create Key Vault**
   - Provision Key Vault via Terraform (`ops/infra/terraform/main.tf`).
2. **Create secret namespace**
   - Use a dedicated prefix per environment (e.g., `prod-`, `staging-`).
3. **Seed baseline secrets**
   - Database connection strings
   - Redis connection strings
   - JWT signing keys and JWKS URL
   - Connector API credentials (Jira, ServiceNow, Azure DevOps)
4. **Configure Kubernetes CSI driver**
   - Apply `ops/infra/kubernetes/secret-provider-class.yaml`.
   - Verify workloads mount secrets at runtime.
   - Ensure the workload identity service account in `ops/infra/kubernetes/service-account.yaml` is annotated with the Key Vault client ID and tenant ID.
   - Confirm pods are labeled with `azure.workload.identity/use: "true"` for AKS workload identity.

### Secret naming and mount conventions

- **Key Vault secret names** should match the filenames expected under `/mnt/secrets-store`.
- **Mount path**: the CSI driver mounts secrets to `/mnt/secrets-store/<secret-name>`.
- **Config references** must use file references, for example:
  - `file:/mnt/secrets-store/identity-client-secret`
  - `file:/mnt/secrets-store/jira-api-token`
- **Local development** can use environment variable placeholders instead of files:
  - `env:IDENTITY_CLIENT_SECRET`
  - `${JIRA_API_TOKEN}`

### Provisioning steps (AKS + Key Vault)

1. **Create/verify Key Vault secrets**
   - Add secrets for endpoints, identity, observability, and connector credentials using the same names referenced in `ops/config/environments/prod.yaml`.
2. **Apply SecretProviderClass**
   - Ensure `ops/infra/kubernetes/secret-provider-class.yaml` lists the secret names to mount.
3. **Deploy workloads**
   - The CSI driver mounts secrets to `/mnt/secrets-store` and optionally syncs them to Kubernetes Secrets via `secretObjects`.

### Validation

- `kubectl describe pod` shows CSI mount ready.
- API gateway `/v1/status` returns `healthy`.
- Identity service can validate JWTs using Key Vault-backed secrets.

### Rotation readiness

- Ensure each secret has an owner, rotation schedule, and alternate version.
- Verify alerting for Key Vault access failures.
- Rotate by updating the Key Vault secret value and restarting pods (or wait for the CSI rotation interval).

---

## Secret Rotation

This section defines procedures for rotating secrets safely across all environments.

### Rotation cadence

- **JWT signing keys:** every 90 days.
- **Database credentials:** every 180 days or upon personnel change.
- **Connector API tokens:** every 90 days.
- **Service principals:** every 180 days.
- **Automated rotation:** a weekly CronJob (`0 3 * * 0`) in the `ppm` namespace rotates all Key Vault secrets and restarts deployments to pick up new values.

### Automation workflow

- **CronJob:** `ops/infra/kubernetes/secret-rotation-cronjob.yaml` runs `mcr.microsoft.com/azure-cli:latest` with the `ppm-admin` service account.
- **Script ConfigMap:** `ops/infra/kubernetes/secret-rotation-scripts.yaml` mounts `rotate_secrets.sh` at `/scripts`.
- **Rotation behaviour:** the script replaces every Key Vault secret with a new 32-byte hex value and triggers rollouts for workflow-service, notification-service, data-service, policy-engine, identity-access, telemetry-service, and audit-log deployments.

### Rotation process

1. **Generate new secret value** in Azure Key Vault.
2. **Stage the new secret** alongside the existing version.
3. **Update configuration** to reference the new version (Key Vault version pin or updated secret name).
4. **Roll deployments** to pick up new secrets.
5. **Validate** authentication, connectors, and workflows.
6. **Revoke old secret** after validation completes.

### Validation checks

- API `/v1/status` returns `healthy`.
- Connector sync jobs authenticate successfully.
- Audit log events continue to ingest.

### Emergency rotation

- Trigger immediate rotation if a compromise is suspected.
- Notify the security team and update the incident record.
- Force logout of all user sessions if JWT signing keys are rotated.

### Tracking

- Record rotation date, owner, and next due date in the secrets inventory.
- Use Key Vault access logs to confirm rotation success.

---

## Schema Promotion and Rollback

Provide a safe, repeatable rollback path when a promoted schema version causes ingestion or downstream processing failures in staging or production environments.

### Triggers

- Spike in `4xx/5xx` responses on data-service ingest endpoints after a schema promotion.
- Validation errors indicating incompatible payloads for recently promoted schema versions.
- Consumer failures in analytics or workflow systems tied to new schema fields.

### Preconditions

1. Identify the impacted schema and promoted version (`<schema>@<bad_version>`).
2. Identify the last known good promoted version (`<schema>@<good_version>`).
3. Confirm blast radius (environments, tenants, connector feeds).

### Rollback procedure

1. **Freeze new promotions and ingesters**
   - Pause promotion pipelines and disable scheduled ingest jobs for impacted connectors.
2. **Re-promote last known good version**
   - Execute:
     - `POST /v1/schemas/<schema>/versions/<good_version>/promote`
     - Body: `{ "environment": "<env>" }`
3. **Validate environment promotion records**
   - Verify `GET /v1/schemas/<schema>/promotions` includes `<good_version>` for `<env>` as the latest effective promotion.
4. **Replay or repair failed ingests**
   - Re-run failed connector sync jobs and inspect validation error counts.
5. **Communicate incident status**
   - Update the incident channel and status page with rollback completion and current ingestion status.

### Verification checklist

- Ingestion for the impacted schema succeeds in `<env>`.
- Error budget burn rate returns to baseline.
- No new incompatible payload errors for `<schema>`.
- Monitoring dashboards reflect healthy throughput and latency.

### Post-incident actions

- Open a follow-up PR to fix the schema change with compatible evolution.
- Update `data/schemas/examples/<schema>.json` with corrective payload snapshots.
- Add or expand compatibility tests in `services/data-service/tests/`.

---

## Credential Acquisition

This section explains how operators obtain credentials required to deploy and operate the platform.

### Azure access

1. Request Azure subscription access through the access management portal.
2. Ensure you have `Contributor` and `Key Vault Secrets Officer` roles for the target resource group.
3. Verify access:
   ```bash
   az account show
   az keyvault secret list --vault-name <vault-name>
   ```

### CI/CD service principal

1. Create a service principal scoped to the resource group:
   ```bash
   az ad sp create-for-rbac \
     --name "ppm-cicd" \
     --role contributor \
     --scopes /subscriptions/<subscription-id>/resourceGroups/<rg>
   ```
2. Store the output in the CI secrets vault (`AZURE_CREDENTIALS`).
3. Grant Key Vault access for secret retrieval.

### Database credentials

- Retrieve database connection strings from Key Vault.
- Validate connectivity using `psql` or application health checks.

### Connector credentials

- **Jira:** create an API token under your Atlassian account and store it in Key Vault.
- **ServiceNow:** create an integration user with read permissions.
- **Azure DevOps:** create a PAT with `Project & Team` read scopes.

### OIDC and SCIM provisioning credentials

1. Register an OIDC application in your IdP (Okta, Entra ID, Auth0, etc.).
2. Configure the redirect URI: `https://<web-host>/oidc/callback`.
3. Add custom claims:
   - `tenant_id` (string) for tenant routing.
   - `roles` (array/string) for RBAC role mapping.
4. Store the client secret in the secrets vault:
   - `OIDC_CLIENT_SECRET` (use an env/file reference in the runtime config).
5. Generate a long-lived SCIM provisioning token and store it in the secrets vault:
   - `SCIM_SERVICE_TOKEN` (use an env/file reference in the runtime config).
6. Distribute the SCIM base URL and token to the IdP provisioning connector:
   - `https://<identity-access-host>/scim/v2`
7. Rotate `SCIM_SERVICE_TOKEN` by issuing a new token, updating the secret reference, restarting `identity-access`, and updating the IdP connector with the new bearer token.

### Least privilege checklist

- [ ] Remove unused credentials after onboarding.
- [ ] Audit access quarterly.
- [ ] Enforce MFA for interactive accounts.

---

## Docker Compose Profiles

This section documents deterministic local stack startup using Compose profiles:

- `demo`: smallest UX-centric stack for product demos.
- `core`: core platform stack for local development.
- `full`: all first-class app and service processes currently implemented in `apps/*/src/main.py` and `services/*/src/main.py`.

### Profile startup order

Compose enforces health-gated `depends_on` links. The effective startup sequence is:

1. `db`, `redis`
2. Foundational APIs: `workflow-service`, `identity-access`, `data-service`
3. Domain/core APIs: `api`, `orchestration-service`, `policy-engine`, `document-service`, `audit-log`, `notification-service`
4. Extended/full APIs (full profile only): `analytics-service`, `data-lineage-service`, `data-sync-service`, `telemetry-service`, `agent-runtime`, `auth-service`, `realtime-coedit-service`
5. `web`

### Services and ports by profile

#### demo profile

| Service | Host port | Container port | Health endpoint |
|---|---:|---:|---|
| api | 8000 | 8000 | `/healthz` |
| workflow-service | 8080 | 8080 | `/healthz` |
| web | 8501 | 8501 | `/healthz` |
| db | 5432 | 5432 | `pg_isready` |
| redis | 6379 | 6379 | `redis-cli ping` |

#### core profile

Includes all `demo` services, plus:

| Service | Host port | Container port | Health endpoint |
|---|---:|---:|---|
| identity-access | 8081 | 8080 | `/healthz` |
| data-service | 8082 | 8080 | `/healthz` |
| policy-engine | 8083 | 8080 | `/healthz` |
| notification-service | 8084 | 8080 | `/healthz` |
| audit-log | 8085 | 8080 | `/healthz` |
| orchestration-service | 8087 | 8080 | `/healthz` |
| document-service | 8088 | 8080 | `/healthz` |

#### full profile

Includes all `core` services, plus:

| Service | Host port | Container port | Health endpoint |
|---|---:|---:|---|
| analytics-service | 8086 | 8080 | `/healthz` |
| data-lineage-service | 8089 | 8080 | `/healthz` |
| data-sync-service | 8090 | 8080 | `/healthz` |
| telemetry-service | 8091 | 8080 | `/healthz` |
| agent-runtime | 8092 | 8080 | `/healthz` |
| auth-service | 8093 | 8080 | `/healthz` |
| realtime-coedit-service | 8094 | 8080 | `/healthz` |

### Startup commands

```bash
# demo stack
COMPOSE_PROFILES=demo docker-compose --profile demo up --build -d

# core stack (default dev target)
make dev-up

# full stack
make dev-up-full
```

### Readiness validation

#### Compose-level health

```bash
docker-compose ps
```

```bash
docker-compose ps --format json | jq -r '. | "\(.Name)\t\(.State)\t\(.Health)"'
```

#### HTTP health checks

```bash
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8080/healthz
curl -fsS http://localhost:8501/healthz
```

Core additions:

```bash
curl -fsS http://localhost:8081/healthz
curl -fsS http://localhost:8082/healthz
curl -fsS http://localhost:8083/healthz
curl -fsS http://localhost:8084/healthz
curl -fsS http://localhost:8085/healthz
curl -fsS http://localhost:8087/healthz
curl -fsS http://localhost:8088/healthz
```

Full additions:

```bash
curl -fsS http://localhost:8086/healthz
curl -fsS http://localhost:8089/healthz
curl -fsS http://localhost:8090/healthz
curl -fsS http://localhost:8091/healthz
curl -fsS http://localhost:8092/healthz
curl -fsS http://localhost:8093/healthz
curl -fsS http://localhost:8094/healthz
```

### Shutdown

```bash
make dev-down
```
