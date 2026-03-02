# Production Readiness Assessment

**Date:** 2026-02-27
**Platform:** Multi-Agent PPM Platform v1.0.0
**Assessor:** Automated assessment via Claude Code

---

## Executive Summary

The Multi-Agent PPM Platform demonstrates **strong production readiness** across most dimensions. The codebase is well-architected with 25 specialized agents, 16+ microservices, comprehensive CI/CD pipelines, robust security controls, and thorough operational runbooks. The platform targets Azure (AKS + managed services) with Terraform IaC and Helm-based deployments.

**Overall Readiness: READY with caveats** — a small number of items require attention before first production deployment.

### Readiness Scorecard

| Dimension                        | Score  | Status      |
|----------------------------------|--------|-------------|
| Architecture & Design            | 9/10   | Ready       |
| Security                         | 9/10   | Ready       |
| CI/CD Pipeline                   | 9/10   | Ready       |
| Testing                          | 8/10   | Ready       |
| Infrastructure as Code           | 9/10   | Ready       |
| Observability & Monitoring       | 9/10   | Ready       |
| Database & Data Management       | 8/10   | Ready       |
| Operational Runbooks             | 9/10   | Ready       |
| Configuration & Secrets          | 8/10   | Ready       |
| Performance & Scalability        | 7/10   | Conditional |

---

## 1. Architecture & Design (9/10)

### Strengths

- **Microservices architecture**: 16+ independently deployable services with clear domain boundaries (API Gateway, Workflow Service, Identity & Access, Policy Engine, Audit Log, Data Service, Notification, Telemetry, etc.).
- **Agent-based orchestration**: 25 specialized domain agents organized into logical groups (Core Orchestration, Portfolio Management, Delivery Management, Operations Management) with a well-defined base agent contract.
- **Multi-tenant ready**: RBAC and ABAC policy engines, tenant-scoped configuration under `ops/config/tenants/`.
- **Event-driven patterns**: Azure Service Bus and Event Hub integration with event schemas and workflows.
- **Docker Compose profiles**: `demo`, `core`, `full` profiles provide progressive service composition for different environments.
- **Health checks**: Every service in `docker-compose.yml` has `healthcheck` and `depends_on` with `condition: service_healthy`.
- **Non-root containers**: Dockerfile creates a dedicated `appuser` (UID 10001) and runs as non-root.

### Concerns

- **Monorepo complexity**: All 25 agents, 16 services, and 40+ connectors in a single repository. Build times and merge contention may increase at scale.

---

## 2. Security (9/10)

### Strengths

- **Secret management**: Azure Key Vault integration with CSI driver and workload identity (`ops/infra/kubernetes/secret-provider-class.yaml`). No hardcoded secrets; `.env.example` uses placeholder values (`REPLACE_ME_NOT_A_REAL_PASSWORD`).
- **Secret scanning**: Gitleaks with custom `.gitleaks.toml` config, both as a pre-commit hook and CI workflow (`secret-scan.yml`).
- **Static security analysis**: Bandit, Safety, pip-audit, Trivy (container + filesystem), and Checkov (IaC) all run in CI.
- **Container security**: Multi-stage Docker builds, non-root user, container image scanning via Trivy in CI.
- **Network security**: Kubernetes NetworkPolicies enforce default-deny with explicit service-to-service allowlists (`ops/infra/kubernetes/manifests/network-policies.yaml`).
- **Pod Security Admission**: Namespace labels set to `restricted` enforce mode (`ops/infra/kubernetes/manifests/pod-security.yaml`).
- **WAF**: Azure Application Gateway WAF v2 with OWASP 3.2 managed ruleset in Prevention mode.
- **TLS enforcement**: PostgreSQL (`TLS1_2`), Redis (`minimum_tls_version = "1.2"`, `enable_non_ssl_port = false`), Storage (`min_tls_version = TLS1_2`).
- **Private networking**: All Azure resources (ACR, Redis, Key Vault, Storage, OpenAI, CosmosDB, Service Bus) have private endpoints; `public_network_access_enabled = false`.
- **Auth patterns**: OIDC-based identity, JWT validation, dev-mode bypass clearly gated by `AUTH_DEV_MODE` flag.
- **SECURITY.md**: Responsible disclosure policy with clear SLAs.
- **Secret rotation**: Kubernetes CronJob for automated secret rotation (`secret-rotation-cronjob.yaml`).
- **Data classification**: Retention policies mapped to classification tiers (public: 30d, internal: 365d, confidential: 5yr, restricted: 7yr).
- **Immutable audit storage**: Blob immutability policies with legal hold on audit-events container.

### Concerns

- **`AUTH_DEV_MODE` safeguard**: Ensure `AUTH_DEV_MODE=true` is impossible to set in staging/production (e.g., via environment schema validation or Helm values assertions). The env validation framework exists (`make env-validate`) but verify it blocks dev-mode flags in non-dev environments.

### Recommendations

1. Add a CI check or OPA policy that explicitly blocks `AUTH_DEV_MODE=true` in staging/production Helm values.
2. Consider adding DAST against a running staging instance (the existing `run_dast.py` appears to be a static analysis wrapper).

---

## 3. CI/CD Pipeline (9/10)

### Strengths

- **Comprehensive CI** (`ci.yml` — 15+ jobs):
  - Linting: Ruff, Black, MyPy
  - Schema/config validation: JSON schemas, manifests, API versioning, connector maturity
  - Security scans: Bandit, Safety, Checkov, Gitleaks, Trivy
  - Testing: Unit (matrix: Python 3.11/3.12), integration, E2E, policy, MCP, contract tests
  - Frontend: Vitest with coverage, API boundary validation
  - Infrastructure: Terraform validate + fmt, Helm lint + template
  - Documentation: Link check, placeholder scan, MkDocs build
  - Performance: Load tests on main merges, performance smoke on PRs with PR comment
  - Python 3.13 cross-platform compatibility (Ubuntu + Windows)
  - Docker image builds for all 16 services with GHCR push
  - Quickstart smoke and full platform demo coverage gates

- **CD Pipeline** (`cd.yml`):
  - Image verification stage pulls and inspects all 16 service images.
  - Staging deployment via Helm with `--atomic`, `--wait`, and automatic rollback on failure.
  - Production deployment with manual approval gate (GitHub environment protection).
  - Image tag validation (regex guard against injection).
  - Max parallelism limits (staging: 4, production: 2) for controlled rollout.

- **Additional pipelines**: Container scan, dependency audit, IaC scan, license compliance, SBOM generation, secret scan, release gate, promotion, visual regression (Storybook), performance smoke.

- **Pinned actions**: All GitHub Actions use commit SHAs rather than mutable tags.

- **Coverage gate**: `--cov-fail-under=80` enforced in CI.

### Concerns

- **Staging smoke tests**: The CD pipeline deploys to staging but does not run automated smoke/E2E tests against the deployed staging environment before promoting to production. Adding a post-deploy validation step would strengthen the pipeline.

### Recommendations

1. Add a post-deployment smoke test job in `cd.yml` between `deploy-staging` and `deploy-production` that hits `/healthz` and runs a lightweight E2E scenario against staging.
2. Consider adding a canary deployment strategy for production (the deployment runbook mentions it, but the CD pipeline does a full rollout).

---

## 4. Testing (8/10)

### Strengths

- **188 test files** across 30 test directories covering agents, apps, services, connectors, contracts, E2E, security, load, performance, LLM, policies, observability, and more.
- **Test taxonomy**: Unit, integration, E2E, security, contract, load, performance — each with dedicated Makefile targets and CI jobs.
- **Coverage target**: 80% enforced in CI.
- **Test infrastructure**: PostgreSQL and Redis service containers in CI for realistic integration tests.
- **Contract tests**: Service API governance tests validate inter-service contracts.
- **Security tests**: Dedicated `tests/security/` with baseline compliance checks.
- **Load testing**: Locust-based load tests with configurable profiles and PR-level performance smoke.
- **Async support**: `pytest-asyncio` for async test patterns.
- **Timeout enforcement**: Global 60s timeout on tests to prevent hangs.

### Concerns

- **E2E coverage breadth**: While E2E tests exist, the full 25-agent orchestration flow may not be fully exercised in CI (the demo coverage gate validates fixture presence and smoke execution but may not cover all failure paths).
- **Frontend test coverage**: Frontend tests run with coverage but the threshold is not explicitly enforced in CI (unlike backend's `--cov-fail-under=80`).

### Recommendations

1. Enforce a minimum frontend coverage threshold in the CI job.
2. Add chaos/fault-injection tests for service-to-service communication failures (circuit breaker and retry validation).

---

## 5. Infrastructure as Code (9/10)

### Strengths

- **Terraform modules**: Well-organized module structure (`aks`, `keyvault`, `monitoring`, `networking`, `postgresql`, `cost-analysis`) with environment overlays (dev, stage, prod, demo, test).
- **Comprehensive Azure resources**: AKS, PostgreSQL Flexible Server (zone-redundant HA), Redis Premium, Cosmos DB, OpenAI, Service Bus, Storage (Data Lake Gen2), ACR, Application Gateway WAF v2, Key Vault.
- **Validation rules**: Extensive `validation` blocks on Terraform variables (SKU names, backup retention ranges, TLS versions, storage replication).
- **Remote state**: Azure Storage backend for Terraform state with per-environment state keys.
- **Private endpoints**: Every Azure PaaS service has a private endpoint configured.
- **Diagnostic settings**: Azure Monitor diagnostic settings for Key Vault, Storage, Service Bus, ACR, and AKS.
- **Monitoring thresholds**: Parameterized alert thresholds (error rate, latency, CPU/memory, DB failures, auth failures, availability, cert expiry, backup failures).
- **Backup automation**: Kubernetes CronJob for PostgreSQL backups (`db-backup-cronjob.yaml`).
- **Disaster recovery**: DR scripts (`failover.sh`, `restore.sh`) under `ops/infra/terraform/dr/`.
- **Resource quotas and limits**: Kubernetes `resource-quotas.yaml` defined.
- **Cert-manager**: Issuer manifest for automated TLS certificate management.
- **Istio mTLS**: Service mesh manifest for mutual TLS between services.

### Concerns

- **Application Gateway HTTP only**: The Terraform `main.tf` configures the Application Gateway listener on port 80 (HTTP) without an HTTPS listener or TLS certificate. For production, HTTPS must be configured.

### Recommendations

1. Add an HTTPS listener (port 443) with a TLS certificate to the Application Gateway configuration in Terraform.
2. Add an HTTP-to-HTTPS redirect rule.

---

## 6. Observability & Monitoring (9/10)

### Strengths

- **OpenTelemetry**: Dedicated OTel collector with Helm chart (`ops/infra/observability/otel/`), configurable exporters including Azure Monitor.
- **Dashboards**: Pre-built Grafana dashboards for platform overview, SLO tracking, and error budgets (`ops/infra/observability/dashboards/`).
- **Alerts**: Parameterized alert rules (`ops/infra/observability/alerts/ppm-alerts.yaml`).
- **SLOs**: SLO definitions (`ops/infra/observability/slo/ppm-slo.yaml`).
- **Health endpoints**: Every service exposes `/healthz` with consistent health check patterns.
- **Prometheus metrics**: `prometheus-client` in dependencies for application-level metrics.
- **Azure Monitor integration**: `azure-monitor-opentelemetry` SDK for traces and metrics.
- **Diagnostic settings**: All Azure resources have Log Analytics diagnostic settings.
- **Runbooks**: Monitoring dashboards, SLO/SLI, incident response, troubleshooting, on-call, and LLM degradation runbooks.

### Concerns

- **Structured logging consistency**: Pre-commit hook blocks f-string logger calls, but verify all services use the shared observability package for consistent structured logging format.

---

## 7. Database & Data Management (8/10)

### Strengths

- **PostgreSQL**: Primary data store with SQLAlchemy 2.0 ORM and Alembic for migrations.
- **Production DB**: Azure PostgreSQL Flexible Server with zone-redundant HA, geo-redundant backups, 35-day retention, TLS 1.2 enforcement, private endpoints.
- **Redis**: Azure Cache for Redis (Premium tier) with persistence, TLS-only, private endpoint.
- **Backup automation**: Kubernetes CronJob for database backups with scripts (`db-backup-cronjob.yaml`, `db-backup-scripts.yaml`).
- **Migration tooling**: `make db-migrate`, `make db-rollback`, registry consistency validation in CI.
- **Schema validation**: JSON schema validation for data entities, schema registry with version tracking.
- **Data lineage**: Dedicated data lineage service for tracking data provenance.
- **Retention policies**: Classification-based retention rules enforced via Azure Storage lifecycle policies.
- **Immutable audit storage**: Locked immutability policy on audit-events container.

### Concerns

- **Connection pooling configuration**: Verify SQLAlchemy connection pool settings (pool_size, max_overflow, pool_timeout) are tuned for production load. The pyproject.toml constrains SQLAlchemy to <2.1 pending async engine migration validation — ensure this is tracked.
- **Migration rollback safety**: The deployment runbook mentions reviewing migrations for "lock risk and rollback compatibility" but there's no automated gate for this.

### Recommendations

1. Document and enforce SQLAlchemy pool settings per environment (dev vs. production).
2. Add a CI check that validates migration rollback compatibility (e.g., ensure each migration has a working `downgrade()` function).

---

## 8. Configuration & Secrets Management (8/10)

### Strengths

- **Environment separation**: Distinct config overlays for dev, staging, production in Terraform and Helm.
- **Secret injection**: Azure Key Vault CSI driver with SecretProviderClass and workload identity — no plaintext secrets in Helm values or Kubernetes manifests.
- **Environment validation**: `make env-validate` validates environment configuration against schemas.
- **Feature flags**: Dedicated feature flag configuration (`ops/config/feature-flags/`).
- **`.env.example` with warnings**: Clear dev-only warning banner; placeholder values that won't work in production.
- **Config validator**: `ops/tools/config_validator.py` runs in CI.
- **Parameterized Helm values**: `values-template.yaml` with environment placeholders.
- **Credential acquisition runbook**: `docs/runbooks/credential-acquisition.md`.

### Concerns

- **Environment drift**: With 30+ environment variables and many per-service configurations, manual parity between environments can drift. Consider a centralized config validation that compares staging and production variable sets.

### Recommendations

1. Add a CI job that validates all required environment variables are defined in staging and production variable groups (or Key Vault entries).
2. Document a configuration parity checklist for promotions.

---

## 9. Operational Readiness (9/10)

### Strengths

- **Comprehensive runbooks**: 16 operational runbooks covering deployment, backup/recovery, disaster recovery, incident response, monitoring, secret rotation, on-call procedures, troubleshooting, quickstart, LLM degradation, and more.
- **Deployment runbook**: Detailed pre/during/post-deployment procedures with checklists, rollback procedures, and validation timelines (60-min and 24-hr).
- **Release process**: Documented release cadence, versioning, maturity score gating, pre-release checklist, and rollback guidance.
- **Disaster recovery**: DR scripts for failover and restore.
- **On-call procedures**: Documented in `docs/runbooks/oncall.md`.
- **Security review**: Recent security review (`docs/production-readiness/security-review-2026-02.md`).
- **Maturity model**: Engineering maturity scoring with ratchet thresholds for continuous improvement.

---

## 10. Performance & Scalability (7/10)

### Strengths

- **Load testing framework**: Locust-based load tests with configurable profiles and baseline comparison.
- **Performance benchmarks**: Automated performance smoke tests on PRs with summary comments.
- **HPA**: Mentioned in production readiness checklist (Kubernetes HPA for CPU autoscaling).
- **AKS autoscaling**: User node pool configured with min/max count (2-6 nodes).
- **Rate limiting**: Environment variables for workflow service and notification service rate limits.
- **Redis caching**: Premium tier Redis with `allkeys-lru` eviction policy.

### Concerns

- **Production worker configuration**: The production Uvicorn command (`make run-api-prod`) uses `--workers 4` but this is a Makefile target — the Dockerfile CMD does not include workers. For production Kubernetes deployment, worker count should be configured via Helm values or entrypoint arguments.
- **LLM latency**: With 25 agents potentially making LLM calls, cascading latency could impact response times. Circuit breakers and timeout budgets for LLM calls should be validated.
- **Database connection pooling under load**: No explicit pool settings visible in the codebase — relies on SQLAlchemy defaults which may not suit production traffic.

### Recommendations

1. Configure Uvicorn workers in the Dockerfile or Helm chart entrypoint for production.
2. Validate and document LLM call timeout budgets and circuit breaker behavior under load.
3. Tune SQLAlchemy connection pool settings for production workloads.
4. Run a representative load test against a staging environment that mirrors production topology before first deployment.

---

## Deployment Steps

### Prerequisites

1. **Azure subscription** with permissions to create: AKS, PostgreSQL Flexible Server, Redis, Key Vault, Storage, Service Bus, ACR, Application Gateway, OpenAI.
2. **Terraform** >= 1.5.0 installed.
3. **Helm** 3.x and `kubectl` configured.
4. **GitHub secrets** configured for CI/CD:
   - `AZURE_CREDENTIALS` (service principal for Azure login)
   - `KUBE_CONFIG_STAGING`, `KUBE_CONFIG_PROD` (kubeconfig for each environment)
   - `K8S_NAMESPACE_STAGING`, `K8S_NAMESPACE_PROD`
   - `IMAGE_REGISTRY` (ACR login server)
5. **Azure Key Vault** provisioned with required secrets (see `docs/runbooks/secret-init.md`).

### Step 1: Provision Infrastructure

```bash
# Initialize Terraform with production backend
cd ops/infra/terraform
terraform init -backend-config=envs/prod/backend.tfvars

# Review plan
terraform plan -var-file=envs/prod/terraform.tfvars

# Apply (requires approval)
terraform apply -var-file=envs/prod/terraform.tfvars
```

This provisions:
- AKS cluster (zone-redundant, private, with RBAC + AAD integration)
- PostgreSQL Flexible Server (zone-redundant HA, geo-redundant backups)
- Azure Cache for Redis (Premium, TLS-only, persistence enabled)
- Azure Key Vault (with workload identity federation)
- Azure Storage (Data Lake Gen2, immutable audit storage)
- Application Gateway WAF v2 (OWASP 3.2 Prevention mode)
- Azure Service Bus (private endpoint)
- Azure OpenAI (private endpoint)
- Networking (VNet, subnets, NSGs, private DNS zones, private endpoints)
- Monitoring (Log Analytics, alert rules, diagnostic settings)

### Step 2: Initialize Secrets

```bash
# Follow the credential acquisition runbook
# docs/runbooks/credential-acquisition.md

# Populate Key Vault with required secrets
# docs/runbooks/secret-init.md
```

Required secrets in Key Vault:
- Database connection string
- Redis connection string
- Azure OpenAI API key and endpoint
- OIDC identity client secret
- Service Bus connection string
- Audit log encryption key
- Azure Monitor connection string

### Step 3: Deploy Observability Stack

```bash
helm upgrade --install ppm-observability \
  ops/infra/kubernetes/helm-charts/observability \
  --namespace observability \
  --create-namespace \
  --set collectorConfig.exporters.azuremonitor.connection_string="$AZURE_MONITOR_CONNECTION_STRING"
```

### Step 4: Apply Kubernetes Security Policies

```bash
# Namespace with pod security admission
kubectl apply -f ops/infra/kubernetes/manifests/namespace.yaml

# Pod security standards
kubectl apply -f ops/infra/kubernetes/manifests/pod-security.yaml

# Network policies (default-deny + allowlists)
kubectl apply -f ops/infra/kubernetes/manifests/network-policies.yaml

# Resource quotas
kubectl apply -f ops/infra/kubernetes/manifests/resource-quotas.yaml

# Service account with workload identity
kubectl apply -f ops/infra/kubernetes/service-account.yaml

# Secret provider class (Key Vault CSI)
kubectl apply -f ops/infra/kubernetes/secret-provider-class.yaml

# Cert-manager issuer
kubectl apply -f ops/infra/kubernetes/manifests/cert-manager-issuer.yaml

# Istio mTLS (if using service mesh)
kubectl apply -f ops/infra/kubernetes/manifests/istio-mtls.yaml
```

### Step 5: Run Database Migrations

```bash
make db-migrate
```

### Step 6: Deploy Services (Dependency Order)

Deploy services via the CD pipeline (`cd.yml`) or manually via Helm in this order:

```bash
NAMESPACE=ppm-platform
REGISTRY=<your-acr>.azurecr.io
TAG=<release-tag>

# 1. Identity & Access
helm upgrade --install identity-access services/identity-access/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/identity-access --set image.tag=$TAG --atomic --wait

# 2. Policy Engine
helm upgrade --install policy-engine services/policy-engine/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/policy-engine --set image.tag=$TAG --atomic --wait

# 3. Data Service
helm upgrade --install data-service services/data-service/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/data-service --set image.tag=$TAG --atomic --wait

# 4. Audit Log
helm upgrade --install audit-log services/audit-log/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/audit-log --set image.tag=$TAG \
  --set keyVault.name=$KV_NAME --set keyVault.tenantId=$KV_TENANT --set keyVault.clientId=$KV_CLIENT --atomic --wait

# 5. Notification Service
helm upgrade --install notification-service services/notification-service/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/notification-service --set image.tag=$TAG --atomic --wait

# 6. Telemetry Service
helm upgrade --install telemetry-service services/telemetry-service/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/telemetry-service --set image.tag=$TAG --atomic --wait

# 7. Data Lineage Service
helm upgrade --install data-lineage-service services/data-lineage-service/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/data-lineage-service --set image.tag=$TAG --atomic --wait

# 8. Data Sync Service
helm upgrade --install data-sync-service services/data-sync-service/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/data-sync-service --set image.tag=$TAG --atomic --wait

# 9. Workflow Service
helm upgrade --install workflow-service apps/workflow-service/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/workflow-service --set image.tag=$TAG --atomic --wait

# 10. Orchestration Service
helm upgrade --install orchestration-service apps/orchestration-service/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/orchestration-service --set image.tag=$TAG --atomic --wait

# 11. Document Service
helm upgrade --install document-service apps/document-service/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/document-service --set image.tag=$TAG --atomic --wait

# 12. Analytics Service
helm upgrade --install analytics-service apps/analytics-service/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/analytics-service --set image.tag=$TAG --atomic --wait

# 13. Connector Hub
helm upgrade --install connector-hub integrations/apps/connector-hub/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/connector-hub --set image.tag=$TAG --atomic --wait

# 14. Admin Console
helm upgrade --install admin-console apps/admin-console/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/admin-console --set image.tag=$TAG --atomic --wait

# 15. Web Console
helm upgrade --install web apps/web/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/web --set image.tag=$TAG --atomic --wait

# 16. API Gateway (last — front door)
helm upgrade --install api-gateway apps/api-gateway/helm \
  --namespace $NAMESPACE --set image.repository=$REGISTRY/api-gateway --set image.tag=$TAG --atomic --wait
```

### Step 7: Post-Deployment Validation

```bash
# Health checks
curl -f https://<api-domain>/healthz
curl -f https://<api-domain>/v1/docs

# Smoke test
python ops/scripts/quickstart_smoke.py

# Verify monitoring
# - Check Grafana dashboards for all services reporting
# - Verify OTel traces are flowing to Azure Monitor
# - Confirm alert rules are active
```

### Step 8: Enable Backup and Rotation Jobs

```bash
# Database backup CronJob
kubectl apply -f ops/infra/kubernetes/db-backup-cronjob.yaml
kubectl apply -f ops/infra/kubernetes/db-backup-scripts.yaml
kubectl apply -f ops/infra/kubernetes/db-backup-secret.yaml

# Secret rotation CronJob
kubectl apply -f ops/infra/kubernetes/secret-rotation-cronjob.yaml
kubectl apply -f ops/infra/kubernetes/secret-rotation-scripts.yaml
```

---

## Pre-Production Checklist

### Critical (must fix before production)

- [ ] **HTTPS on Application Gateway**: Add HTTPS listener (port 443) with TLS certificate to the Terraform Application Gateway configuration. The current config only has an HTTP listener on port 80.
- [ ] **Uvicorn worker config**: Ensure the Helm chart or Dockerfile entrypoint includes `--workers` flag for production (current Dockerfile CMD runs a single worker).
- [ ] **AUTH_DEV_MODE guard**: Verify `AUTH_DEV_MODE=true` cannot be set in production via environment validation or Helm values assertions.

### Important (should address for first deployment)

- [ ] **SQLAlchemy pool tuning**: Configure `pool_size`, `max_overflow`, `pool_timeout` for production database connections.
- [ ] **Staging smoke tests in CD**: Add post-deploy validation in `cd.yml` between staging and production deployment.
- [ ] **Frontend coverage threshold**: Enforce minimum coverage in the frontend CI job.
- [ ] **LLM timeout budgets**: Document and validate timeout budgets for LLM-dependent agent calls under load.

### Recommended (good practice)

- [ ] **Configuration parity validation**: Add CI check comparing staging and production variable completeness.
- [ ] **Migration rollback testing**: Add CI gate validating each Alembic migration has a working `downgrade()`.
- [ ] **Production load test**: Run a full representative load test against a staging environment mirroring production topology.
- [ ] **DAST against staging**: Run dynamic application security testing against a deployed staging instance.

---

## Related Documents

- [Production Readiness Checklist](./checklist.md)
- [Release Process](./release-process.md)
- [Security Baseline](./security-baseline.md)
- [Security Review (Feb 2026)](./security-review-2026-02.md)
- [Maturity Model](./maturity-model.md)
- [Deployment Runbook](../runbooks/deployment.md)
- [Backup & Recovery](../runbooks/backup-recovery.md)
- [Disaster Recovery](../runbooks/disaster-recovery.md)
- [Incident Response](../runbooks/incident-response.md)
- [Secret Rotation](../runbooks/secret-rotation.md)
- [Monitoring Dashboards](../runbooks/monitoring-dashboards.md)
- [SLO/SLI Reference](../runbooks/slo-sli.md)
