# Production Readiness

> This hub consolidates all production readiness documentation for the Multi-Agent PPM Platform: the pre-launch checklist, engineering maturity model and scorecards, full production readiness assessment, end-to-end release process, minimum security baseline controls, and the evidence pack. Use these documents together to validate that the platform is fit for production deployment and to track ongoing engineering quality.

## Contents

- [Checklist](#checklist) — Infrastructure, security, application, CI/CD, and verification items that must pass before deployment.
- [Maturity Model](#maturity-model) — Eight-dimension engineering maturity framework with KPI definitions, ratchet thresholds, and CI integration.
- [Assessment](#assessment) — Detailed readiness assessment scored across ten dimensions (date: 2026-02-27), including deployment steps and pre-production checklist.
- [Release Process](#release-process) — End-to-end release workflow: cadence, versioning, quality gates, tagging steps, and rollback guidance.
- [Security Baseline](#security-baseline) — Minimum required security controls mapped to implementation locations, with automated enforcement tooling.
- [Evidence Pack](#evidence-pack) — Single-source build, test, scan, deploy, and operate reference with acceptance criteria checklist.
- [Security Review (February 2026)](#security-review-february-2026) — Full architecture and security review report with findings, fixes, and test coverage added.
- [Maturity Scorecards](#maturity-scorecards) — Generated scorecard snapshots and monthly improvement backlog.

---

## Checklist

> Source: checklist.md

### Infrastructure

- [ ] Terraform plan reviewed for AKS, networking, storage, WAF, and monitoring resources.
- [ ] Private AKS cluster reachable via approved network path (jump box or VPN).
- [ ] Azure Front Door/App Gateway WAF policy applied and in prevention mode.
- [ ] Immutable audit log storage enabled with retention policy locked.

### Security

- [ ] Key Vault CSI + workload identity configured for all workloads.
- [ ] Secrets injected via CSI, no plaintext values in Helm values.
- [ ] NetworkPolicies enforced (default deny + explicit service allowlists).
- [ ] Pod Security Admission labels set to `restricted`.
- [ ] Secret scan and IaC scan workflows passing.

### Application

- [ ] Frontend API calls use shared `requestJson` helper (no raw `fetch` in pages/components) and expose retry + user-facing error states.
- [ ] Helm charts linted and rendered without errors.
- [ ] HPA configured for CPU autoscaling.
- [ ] Rate limiting and CORS policies validated in production mode.
- [ ] OTel collector deployed and exporting traces/metrics.

### CI/CD

- [ ] E2E and contract tests passing on main.
- [ ] Terraform validate + helm lint/template checks passing.
- [ ] SBOM generated and attached to release tags.
- [ ] Documentation build passes (`mkdocs build`).

### Verification

- [ ] Runbooks updated and linked.
- [ ] Load test profile meets SLA targets.

---

## Maturity Model

> Source: maturity-model.md

### Purpose

Define an objective and enforceable maturity model that converts delivery, operational, and governance signals into a release decision.

### Dimensions and KPI definitions

The model is encoded in [Maturity Model](../../ops/config/maturity_model.yaml) and scored by [Collect Maturity Score](../../ops/tools/collect_maturity_score.py).

| Dimension | Example KPIs (measurable) | Target intent |
| --- | --- | --- |
| Reliability | `slo_pass_rate`, `mttr_minutes` | SLO adherence + faster incident recovery |
| Scalability | `p95_latency_ms`, `headroom_percent` | Capacity and latency resilience under load |
| Security | `critical_vulnerability_count`, `secret_findings` | Zero critical findings at release time |
| Operability | `alert_actionability_percent`, `config_drift_violations` | Reduce alert noise and drift |
| Test Coverage | `backend_coverage_percent`, `frontend_coverage_percent` | Coverage baseline with incremental uplift |
| Documentation | `stale_doc_count`, `runbook_sla_percent` | Fresh docs and runbooks tied to changes |
| DR/Backup | `backup_success_percent`, `restore_rto_minutes` | Proven backup reliability + restore readiness |
| Dependency Hygiene | `dependency_age_p95_days`, `unpinned_dependency_count` | Healthy patch currency and deterministic builds |

Each KPI defines:

- artifact source (`artifacts/.../*.json`)
- JSON path selector
- scoring direction (`higher_is_better` / `lower_is_better`)
- floor and target bounds for 0–100 score normalization

### Release eligibility thresholds

Release is eligible only if all conditions pass:

1. Overall weighted score >= `minimum_overall_score`.
2. Every dimension score >= `minimum_dimension_score`.
3. Mandatory dimensions (`Reliability`, `Security`, `Test Coverage`) also meet the dimension threshold.

Current baseline policy is stored in `release_policy` and enforced by:

```bash
python ops/tools/collect_maturity_score.py --enforce-thresholds
```

### Ratcheting policy

Thresholds increase quarterly through the `ratchet_policy.schedule` table in `ops/ops/config/maturity_model.yaml`.

- The collector resolves the active threshold set by `effective_date`.
- Teams should only move thresholds upward (no downward edits) unless an incident postmortem approves an exception.
- Ratchet updates should land before the first release planning cycle of each quarter.

### Publishing snapshots and backlog generation

The collector writes:

- JSON scorecard: `artifacts/maturity/scorecard-latest.json`
- Markdown snapshot: `docs/production-readiness/maturity-scorecards/latest.md`

The scorecard includes a **monthly backlog** generated from the three lowest-scoring dimensions. Product/engineering planning should create explicit backlog items from this section each month.

### CI usage

```bash
python ops/tools/collect_maturity_score.py --artifact-root . --enforce-thresholds
```

Publish the JSON and markdown outputs as workflow artifacts so the release decision is auditable and trendable over time.

---

## Assessment

> Source: production-readiness-assessment.md

**Date:** 2026-02-27
**Platform:** Multi-Agent PPM Platform v1.0.0
**Assessor:** Automated assessment via Claude Code

### Executive Summary

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

### 1. Architecture & Design (9/10)

**Strengths**

- **Microservices architecture**: 16+ independently deployable services with clear domain boundaries.
- **Agent-based orchestration**: 25 specialized domain agents organized into four logical groups with a well-defined base agent contract.
- **Multi-tenant ready**: RBAC and ABAC policy engines, tenant-scoped configuration under `ops/config/tenants/`.
- **Event-driven patterns**: Azure Service Bus and Event Hub integration with event schemas and workflows.
- **Docker Compose profiles**: `demo`, `core`, `full` profiles provide progressive service composition.
- **Health checks**: Every service in `docker-compose.yml` has `healthcheck` and `depends_on` with `condition: service_healthy`.
- **Non-root containers**: Dockerfile creates a dedicated `appuser` (UID 10001).

**Concerns**

- **Monorepo complexity**: All 25 agents, 16 services, and 40 connectors in a single repository — build times and merge contention may increase at scale.

### 2. Security (9/10)

**Strengths**

- Azure Key Vault integration with CSI driver and workload identity. No hardcoded secrets.
- Gitleaks secret scanning in both pre-commit and CI.
- Static analysis: Bandit, Safety, pip-audit, Trivy, and Checkov all run in CI.
- Kubernetes NetworkPolicies enforce default-deny with explicit service-to-service allowlists.
- Pod Security Admission: namespace labels set to `restricted`.
- Azure Application Gateway WAF v2 with OWASP 3.2 managed ruleset in Prevention mode.
- TLS 1.2 enforced on PostgreSQL, Redis, and Storage.
- All Azure PaaS resources use private endpoints; `public_network_access_enabled = false`.
- Secret rotation via Kubernetes CronJob.
- Data classification retention policies (public: 30d, internal: 365d, confidential: 5yr, restricted: 7yr).
- Immutable audit storage with legal hold on audit-events container.

**Concerns and recommendations**

- Ensure `AUTH_DEV_MODE=true` cannot be set in staging/production (via env schema validation or Helm assertions).
- Add a CI check or OPA policy that explicitly blocks `AUTH_DEV_MODE=true` in staging/production Helm values.
- Consider adding DAST against a running staging instance.

### 3. CI/CD Pipeline (9/10)

**Strengths**

- 15+ CI jobs: linting, schema validation, security scans, unit/integration/E2E/contract tests, frontend coverage, Terraform validate, Helm lint, documentation build, performance smoke, Docker builds for all 16 services.
- CD pipeline with image verification, staging Helm deployment (`--atomic --wait`), manual production approval gate, and image tag validation.
- All GitHub Actions pinned to commit SHAs.
- Coverage gate: `--cov-fail-under=80` enforced.

**Concerns and recommendations**

- Add a post-deployment smoke test job in `cd.yml` between staging and production that hits `/healthz` and runs a lightweight E2E scenario.
- Consider a canary deployment strategy for production.

### 4. Testing (8/10)

**Strengths**

- 188 test files across 30 test directories: unit, integration, E2E, security, contract, load, performance, LLM, policies, and observability.
- 80% backend coverage enforced.
- PostgreSQL and Redis service containers in CI for realistic integration tests.
- Locust-based load tests with configurable profiles.
- Global 60-second timeout on tests.

**Concerns and recommendations**

- Enforce a minimum frontend coverage threshold in the CI job.
- Add chaos/fault-injection tests for service-to-service communication failures.

### 5. Infrastructure as Code (9/10)

**Strengths**

- Terraform modules: `aks`, `keyvault`, `monitoring`, `networking`, `postgresql`, `cost-analysis` with environment overlays (dev, stage, prod, demo, test).
- Comprehensive Azure resources with zone-redundant HA for PostgreSQL, Premium Redis, Cosmos DB, Service Bus, ACR, Application Gateway WAF v2.
- Remote state in Azure Storage with per-environment state keys.
- Private endpoints for every Azure PaaS service.
- DR scripts (`failover.sh`, `restore.sh`) under `ops/infra/terraform/dr/`.

**Concerns and recommendations**

- The Terraform `main.tf` configures the Application Gateway on port 80 (HTTP) only — add an HTTPS listener (port 443) with a TLS certificate and an HTTP-to-HTTPS redirect rule.

### 6. Observability & Monitoring (9/10)

**Strengths**

- OpenTelemetry collector with Helm chart, configurable exporters including Azure Monitor.
- Pre-built Grafana dashboards for platform overview, SLO tracking, and error budgets.
- Parameterized alert rules and SLO definitions.
- Every service exposes `/healthz`.
- 16 operational runbooks covering all key scenarios.

### 7. Database & Data Management (8/10)

**Strengths**

- Azure PostgreSQL Flexible Server with zone-redundant HA, geo-redundant backups, 35-day retention, TLS 1.2, private endpoints.
- Azure Cache for Redis (Premium tier) with persistence, TLS-only, private endpoint.
- Alembic migrations with `make db-migrate` / `make db-rollback`.
- JSON schema validation for data entities; classification-based retention policies.

**Concerns and recommendations**

- Verify SQLAlchemy connection pool settings (pool_size, max_overflow, pool_timeout) are tuned for production.
- Add a CI check that validates migration rollback compatibility.

### 8. Configuration & Secrets Management (8/10)

**Strengths**

- Azure Key Vault CSI driver with SecretProviderClass and workload identity — no plaintext secrets in Helm or Kubernetes manifests.
- `make env-validate` validates environment configuration against schemas.
- Distinct config overlays for dev, staging, and production.

**Concerns and recommendations**

- Add a CI job that validates all required environment variables are defined in staging and production variable groups.
- Document a configuration parity checklist for promotions.

### 9. Operational Readiness (9/10)

**Strengths**

- 16 operational runbooks: deployment, backup/recovery, disaster recovery, incident response, monitoring, secret rotation, on-call procedures, troubleshooting, quickstart, and LLM degradation.
- DR scripts, maturity model scoring, and a recent security review complement the runbook set.

### 10. Performance & Scalability (7/10)

**Strengths**

- Locust-based load tests with performance smoke tests on PRs.
- AKS user node pool configured with min/max autoscaling (2–6 nodes).
- Premium Redis with `allkeys-lru` eviction policy.

**Concerns and recommendations**

- Configure Uvicorn workers in the Dockerfile or Helm chart entrypoint for production.
- Validate and document LLM call timeout budgets and circuit breaker behaviour under load.
- Tune SQLAlchemy connection pool settings for production workloads.
- Run a representative load test against a staging environment that mirrors production topology before first deployment.

### Deployment Steps

#### Prerequisites

1. Azure subscription with permissions to create: AKS, PostgreSQL Flexible Server, Redis, Key Vault, Storage, Service Bus, ACR, Application Gateway, OpenAI.
2. Terraform >= 1.5.0, Helm 3.x, and `kubectl` configured.
3. GitHub secrets configured: `AZURE_CREDENTIALS`, `KUBE_CONFIG_STAGING`, `KUBE_CONFIG_PROD`, `K8S_NAMESPACE_STAGING`, `K8S_NAMESPACE_PROD`, `IMAGE_REGISTRY`.
4. Azure Key Vault provisioned with required secrets (see `docs/runbooks/secret-init.md`).

#### Step 1: Provision Infrastructure

```bash
cd ops/infra/terraform
terraform init -backend-config=envs/prod/backend.tfvars
terraform plan -var-file=envs/prod/terraform.tfvars
terraform apply -var-file=envs/prod/terraform.tfvars
```

Provisions: AKS, PostgreSQL Flexible Server, Redis, Key Vault, Storage (Data Lake Gen2 + immutable audit), Application Gateway WAF v2, Service Bus, Azure OpenAI, networking, and monitoring.

#### Step 2: Initialize Secrets

Follow Secret Initialization runbook and Credential Acquisition runbook to populate Key Vault with all required secrets.

#### Step 3: Deploy Observability Stack

```bash
helm upgrade --install ppm-observability \
  ops/infra/kubernetes/helm-charts/observability \
  --namespace observability \
  --create-namespace \
  --set collectorConfig.exporters.azuremonitor.connection_string="$AZURE_MONITOR_CONNECTION_STRING"
```

#### Step 4: Apply Kubernetes Security Policies

```bash
kubectl apply -f ops/infra/kubernetes/manifests/namespace.yaml
kubectl apply -f ops/infra/kubernetes/manifests/pod-security.yaml
kubectl apply -f ops/infra/kubernetes/manifests/network-policies.yaml
kubectl apply -f ops/infra/kubernetes/manifests/resource-quotas.yaml
kubectl apply -f ops/infra/kubernetes/service-account.yaml
kubectl apply -f ops/infra/kubernetes/secret-provider-class.yaml
kubectl apply -f ops/infra/kubernetes/manifests/cert-manager-issuer.yaml
kubectl apply -f ops/infra/kubernetes/manifests/istio-mtls.yaml
```

#### Step 5: Run Database Migrations

```bash
make db-migrate
```

#### Step 6: Deploy Services (Dependency Order)

Deploy via the CD pipeline (`cd.yml`) or manually via Helm in dependency order: Identity & Access → Policy Engine → Data Service → Audit Log → Notification → Telemetry → Data Lineage → Data Sync → Workflow → Orchestration → Document → Analytics → Connector Hub → Admin Console → Web Console → API Gateway (last, as the front door).

#### Step 7: Post-Deployment Validation

```bash
curl -f https://<api-domain>/healthz
curl -f https://<api-domain>/v1/docs
python ops/scripts/quickstart_smoke.py
```

Then verify Grafana dashboards, OTel trace flow to Azure Monitor, and alert rule activation.

#### Step 8: Enable Backup and Rotation Jobs

```bash
kubectl apply -f ops/infra/kubernetes/db-backup-cronjob.yaml
kubectl apply -f ops/infra/kubernetes/db-backup-scripts.yaml
kubectl apply -f ops/infra/kubernetes/db-backup-secret.yaml
kubectl apply -f ops/infra/kubernetes/secret-rotation-cronjob.yaml
kubectl apply -f ops/infra/kubernetes/secret-rotation-scripts.yaml
```

### Pre-Production Checklist

#### Critical (must fix before production)

- [ ] **HTTPS on Application Gateway**: Add HTTPS listener (port 443) with TLS certificate. Current config only has HTTP on port 80.
- [ ] **Uvicorn worker config**: Ensure the Helm chart or Dockerfile entrypoint includes `--workers` for production.
- [ ] **AUTH_DEV_MODE guard**: Verify `AUTH_DEV_MODE=true` cannot be set in production via environment validation or Helm values assertions.

#### Important (should address for first deployment)

- [ ] **SQLAlchemy pool tuning**: Configure `pool_size`, `max_overflow`, `pool_timeout` for production database connections.
- [ ] **Staging smoke tests in CD**: Add post-deploy validation in `cd.yml` between staging and production deployment.
- [ ] **Frontend coverage threshold**: Enforce minimum coverage in the frontend CI job.
- [ ] **LLM timeout budgets**: Document and validate timeout budgets for LLM-dependent agent calls under load.

#### Recommended (good practice)

- [ ] **Configuration parity validation**: Add CI check comparing staging and production variable completeness.
- [ ] **Migration rollback testing**: Add CI gate validating each Alembic migration has a working `downgrade()`.
- [ ] **Production load test**: Run a full representative load test against a staging environment mirroring production topology.
- [ ] **DAST against staging**: Run dynamic application security testing against a deployed staging instance.

### Related Documents

- Deployment Runbook
- Backup & Recovery Runbook
- Disaster Recovery Runbook
- Incident Response Runbook
- Secret Rotation Runbook
- Monitoring Dashboards Runbook
- SLO/SLI Reference

---

## Release Process

> Source: release-process.md

### Purpose

Document the end-to-end release workflow for the Multi-Agent PPM Platform, including governance checks, tagging, and post-release validation.

### Release cadence and ownership

- **Cadence:** Monthly minor releases with weekly patch releases as needed.
- **Owners:** Release manager (operations), security lead, product owner.

### Versioning

- Follow **semantic versioning** (`MAJOR.MINOR.PATCH`).
- Update `CHANGELOG.md` before cutting a release tag.

### Pre-release checklist

1. **Backlog readiness** — Confirm approved scope and risk sign-offs; ensure documentation updates are merged.
2. **Quality gates** — CI pipeline green (lint, tests, security scans); coverage ≥ 80% for changed components.
3. **Security & compliance** — DPIA and threat model reviewed for material changes; secrets verified in Key Vault and rotated if required.
4. **Operational readiness** — Runbooks updated for new endpoints or workflows; monitoring dashboards and alerts validated.

### Maturity score gate

- Release readiness is scored using the [Engineering Maturity Model](#maturity-model).
- CI artifacts are consolidated with `python ops/tools/collect_maturity_score.py --enforce-thresholds`.
- A release is blocked when overall or dimension-level ratchet thresholds are not met.
- Monthly planning must pull backlog items from the [latest maturity scorecard](#maturity-scorecards).

### Release steps

1. **Prepare release branch**: Create `release/vX.Y.Z`, update `CHANGELOG.md` and version references.
2. **Tag the release**:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```
3. **CI/CD automation**: `release.yml` builds artifacts, generates SBOM, signs, and verifies signatures; artifacts published to the registry and attached to the release.
4. **Deploy to staging**: Use the Deployment runbook; run smoke tests and verify dashboards.
5. **Promote to production**: Obtain approval from release manager and security lead; deploy with Helm in the documented service order.

### Migration notes (workflow service distributed execution)

- Deploy the Celery broker (Redis or RabbitMQ) before scaling workflow service pods.
- Roll out the `workflow-service` Celery worker deployment alongside the API service.
- Set `WORKFLOW_BROKER_URL` and `WORKFLOW_RESULT_BACKEND` in the environment or Helm values.
- Monitor worker queues for retries; ensure idempotent workflow steps are enabled before cutover.

### Post-release validation

- Confirm `/healthz` for API gateway, workflow service, and core services.
- Verify audit log ingestion and retention policy execution.
- Validate telemetry ingestion and alerting.
- Notify stakeholders in the release channel with summary and rollback plan.

### Rollback guidance

- Identify last known good tag from deployment history.
- Roll back Helm releases to prior chart versions.
- Re-run smoke tests and verify SLO dashboards stabilize.

### Release documentation

- Update `CHANGELOG.md` with release notes.
- Store evidence in the [Evidence Pack](#evidence-pack).

---

## Security Baseline

> Source: security-baseline.md

This baseline defines required controls for all platform services and maps each control to implementation anchors in the repository.

### Scope

- Service applications under `services/*/src/main.py`
- Shared security package in `packages/security/src/security/`
- Policy artifacts under `ops/config/` and `ops/config/data-classification/`

### Required controls and code mappings

| Control area | Baseline requirement | Primary code locations |
| --- | --- | --- |
| Authentication | Protected routes must enforce tenant-aware auth middleware (`AuthTenantMiddleware`) with only `/healthz` and `/version` exempted; only designated identity/auth services may omit this middleware. | `packages/security/src/security/auth.py`, all service `src/main.py` files |
| RBAC / ABAC | Authorization decisions must use policy-backed role/action/resource evaluation and ABAC condition checks. | `services/policy-engine/src/main.py`, `ops/config/rbac/roles.yaml`, `ops/config/abac/rules.yaml` |
| DLP / masking | Sensitive fields and lineage payloads must be masked/redacted before persistence or downstream emission, aligned to classification levels. | `services/data-lineage-service/src/main.py`, `packages/security/src/security/lineage.py`, `ops/config/data-classification/levels.yaml` |
| Secret resolution | Secret-like env vars (`*_SECRET`, `*_TOKEN`, `*_PASSWORD`, `*_KEY`, `*_CONNECTION_STRING`, `*_WEBHOOK`) must be resolved through `security.secrets.resolve_secret` — not consumed as raw plaintext from `os.getenv`. | `packages/security/src/security/secrets.py`, `services/auth-service/src/main.py`, `services/identity-access/src/main.py` |
| Security headers / API governance | Services must apply shared governance and headers middleware (`apply_api_governance`) and include request tracing/metrics middleware. | `packages/security/src/security/api_governance.py`, `packages/security/src/security/headers.py` |
| Auditability | Security-relevant flows must produce immutable audit evidence with retention enforcement and evidence export capability. | `services/audit-log/src/main.py`, `data/schemas/audit-event.schema.json`, `ops/config/retention/policies.yaml` |

### Automated enforcement

- `ops/tools/check_security_middleware.py` enforces security middleware presence and auth exempt-path policy.
- `ops/tools/check_secret_source_policy.py` enforces secret source policy (`resolve_secret` usage).
- `tests/security/test_security_baseline_compliance.py` provides a parameterized cross-service compliance suite.
- `make check-security-baseline` runs all baseline gates.

---

## Evidence Pack

> Source: evidence-pack.md

A single source of truth for how to build, test, scan, deploy, and operate the platform in a production-ready manner.

### Build

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
python -m build --sdist --wheel
```

### Test

```bash
make lint
make test-cov
python ops/scripts/validate-schemas.py
python ops/scripts/validate-manifests.py
python ops/scripts/quickstart_smoke.py
```

### Security & Compliance Scans

```bash
make secret-scan
python ops/scripts/generate-sbom.py
python ops/scripts/sign-artifact.py
python ops/scripts/verify-signature.py
```

CI also runs: Trivy filesystem scan, license compliance, and SAST/SCA workflows.

### Release Process (Tag → Build → SBOM → Sign)

1. Update `CHANGELOG.md` and bump the version in `pyproject.toml`.
2. Tag the release: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`.
3. Push tags to trigger the release workflow.
4. `release.yml` builds artifacts, generates SBOM, signs, and verifies signatures.

### Deploy

```bash
# Kubernetes + Helm
helm dependency build ops/infra/kubernetes/helm-charts/ppm-platform
helm lint ops/infra/kubernetes/helm-charts/ppm-platform \
  --set audit-log.keyVault.name=kv-sample \
  --set audit-log.keyVault.tenantId=tenant-sample \
  --set audit-log.keyVault.clientId=client-sample

# Terraform
make tf-init && make tf-plan && make tf-apply
```

### Operate

- **Runbooks**: `docs/runbooks/` (incident response, backup/recovery, on-call, troubleshooting).
- **Monitoring**: Monitoring Dashboards Runbook.
- **SLO/SLI**: SLO/SLI Reference.

### Acceptance Criteria Checklist

- [x] CI gates: lint, typecheck, tests with coverage ≥ 80%.
- [x] Deterministic quickstart scenario (see Quickstart Runbook).
- [x] Auth dev mode for local stack with RBAC enforcement.
- [x] Orchestration resilience (bounded concurrency, retries, timeouts, caching).
- [x] Release pipeline builds, generates SBOM, signs, and verifies artifacts.
- [x] Runbooks for incident response, backup/recovery, and DR.

---

## Security Review (February 2026)

> Source: security-review-2026-02.md

**Scope:** Full repository review of the Multi-Agent PPM Platform (v4).
**Reviewer:** Senior Software Architect / AI Engineer.
**Branch:** `claude/review-ppm-platform-cknWG`

### Executive Summary

The platform is a well-structured, enterprise-grade AI-native PPM system featuring 25 specialised agents, 16 microservices, a React 18 frontend, 45+ connector integrations, and a comprehensive operational stack (Kubernetes, Helm, Terraform, OpenTelemetry). The review identified **four actionable improvements** spanning security, cloud-provider coverage, and AI safety. All four were implemented and tested. A subsequent February 2026 follow-up pass (`claude/remove-jwt-duplication-sFlwi`) resolved five additional architectural findings.

### Review Findings

#### 2.1 Missing Content-Security-Policy (CSP) Header — Critical

**File:** `packages/security/src/security/headers.py`

The `SecurityHeadersMiddleware` omitted the `Content-Security-Policy` header, leaving the platform without browser-enforced XSS protection. Non-compliance affected Australian Government ISM SC-SC-18, APRA CPS 234 clause 36, and OWASP Top 10 A03:2021.

**Fix applied:** Introduced `_build_csp()` helper with a strict directive set (`default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, `upgrade-insecure-requests`) plus an operator-extensible `CSP_EXTRA_SCRIPT_SRCS` environment variable.

#### 2.2 OIDC Discovery Cache Memory Leak & Stale-Data Risk — High

**File:** `services/api-gateway/src/api/middleware/security.py`

The module-level `_OIDC_CONFIG_CACHE` was a plain unbounded dict: it never evicted entries, never expired stale JWKS data, and was not thread-safe.

**Fix applied:** Replaced with `_OIDCTTLCache` — a thread-safe, bounded LRU cache with per-entry TTL (default 300s, max 32 entries, configurable via env vars).

#### 2.3 Missing Azure OpenAI Provider — High

**Files:** `packages/llm/src/providers/azure_openai_provider.py` (new), `packages/llm/src/router.py`, `apps/web/data/llm_models.json`

The LLM router lacked an Azure OpenAI provider, which is required for Australian Government/regulated-enterprise deployments (data sovereignty, IRAP compliance, APRA CPS 234).

**Fix applied:** Created `AzureOpenAIProvider` with the same `complete()` interface as existing providers. Configured via `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, and `AZURE_OPENAI_API_VERSION`. Two model entries (`gpt-4o`, `gpt-4o-mini`) registered in `llm_models.json`, disabled by default.

#### 2.4 Insufficient Prompt Injection Detection — Medium

**File:** `packages/llm/prompt_sanitizer.py`

The original detection covered seven regex patterns but missed modern jailbreak phrases, credential exfiltration patterns, safety bypass phrasings, chat template injection markers, and Unicode homoglyph bypass.

**Fix applied:** Added 11 new regex patterns and a `_normalise()` helper that applies NFKC Unicode normalization before pattern matching.

### Previously Deferred Findings — Resolved (February 2026 Follow-up)

All five architectural findings deferred in the original review were implemented and tested on branch `claude/remove-jwt-duplication-sFlwi`:

| Finding | Resolution |
|---------|------------|
| **3.1 Auth Code Duplication** | Removed duplicate JWT validation from API Gateway middleware; delegates to `security.auth.authenticate_request()`. Added `clear_auth_caches()` to the security package. |
| **3.2 `sys.path` Manipulation** | Removed `sys.path.insert` blocks from production files; replaced with proper `[tool.setuptools.packages.find]` configuration in `pyproject.toml`. |
| **3.3 LLM Key Rotation** | Added SIGUSR1 signal handler and `POST /v1/admin/llm/keys/rotate` HTTP endpoint (requires `config.write` permission). |
| **3.4 Model Registry Cache Invalidation** | Added `POST /v1/admin/model-registry/cache/clear` endpoint enabling zero-downtime registry updates. |
| **3.5 `on_event` Deprecation** | Replaced deprecated `@app.on_event` decorators with `@asynccontextmanager lifespan` pattern. |

### Test Coverage Added

| Test file | Coverage |
|-----------|----------|
| `tests/security/test_security_headers.py` | CSP directive construction, header presence, HSTS behaviour, env-var extension |
| `tests/security/test_oidc_cache.py` | TTL expiry, LRU eviction, thread-safety, boundary conditions |
| `packages/llm/tests/test_azure_openai_provider.py` | Successful completion, JSON mode, URL correctness, timeout/4xx/429 error handling |
| `tests/llm/test_prompt_sanitizer_enhanced.py` | 23 positive/negative detection cases, Unicode normalization, false-positive guard |
| `tests/security/test_jwt_delegation.py` | Delegation correctness, symbol removal, 401 propagation, exempt paths |
| `tests/security/test_key_rotation.py` | Cache clearing, SIGUSR1 handler, model registry LRU invalidation |
| `tests/test_security_review_fixes.py` | Smoke tests for all five previously deferred findings |

### Production Readiness Score After Review

| Category | Before | After Feb 2026 follow-up |
|----------|--------|--------------------------|
| Architecture | Strong | Strong |
| Observability | Strong | Strong |
| Security headers | Missing CSP | Fixed |
| Auth cache | Memory leak | Fixed |
| AI safety | Partial injection coverage | Improved |
| Cloud compliance (AUS) | No Azure OpenAI | Added |
| Auth code quality | Duplicate JWT logic | Centralised |
| Import hygiene | `sys.path` manipulation | Proper packaging |
| Key rotation | No in-process trigger | SIGUSR1 + HTTP endpoint |
| Registry invalidation | Restart required | Admin endpoint |
| Lifecycle events | Deprecated `on_event` | Lifespan pattern |
| Test coverage | 320+ test files | 39 new tests for follow-up fixes |

---

## Maturity Scorecards

> Source: [Readme](./maturity-scorecards/README.md) and [Latest](./maturity-scorecards/latest.md)

This section stores published maturity score snapshots. `latest.md` is generated by `python ops/tools/collect_maturity_score.py`. CI uploads both `latest.md` and `artifacts/maturity/scorecard-latest.json` for each release-gate run. The monthly backlog in each snapshot should be copied into engineering planning as concrete improvement tickets.

### Latest Scorecard Snapshot

- **Generated at:** 2026-02-18T10:57:50.021329+00:00
- **Overall score:** 100.0
- **Release eligible:** yes
- **Active thresholds:** overall ≥ 75.0, dimension ≥ 65.0

#### Dimension Scores

| Dimension | Score |
| --- | ---: |
| DR/Backup | 100.0 |
| Dependency Hygiene | 100.0 |
| Documentation | 100.0 |
| Operability | 100.0 |
| Reliability | 100.0 |
| Scalability | 100.0 |
| Security | 100.0 |
| Test Coverage | 100.0 |

#### Monthly Backlog (Lowest Scoring Dimensions)

| Rank | Dimension | Score | Focus |
| --- | --- | ---: | --- |
| 1 | Reliability | 100.0 | Raise KPI scores above current ratchet threshold |
| 2 | Scalability | 100.0 | Raise KPI scores above current ratchet threshold |
| 3 | Security | 100.0 | Raise KPI scores above current ratchet threshold |
