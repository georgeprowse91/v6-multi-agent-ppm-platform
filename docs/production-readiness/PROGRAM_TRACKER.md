# Production Readiness Program Tracker

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Fix promotion workflow injection vulnerability in GitHub Actions | Done | `.github/workflows/promotion.yml` input validation, ref restriction, least-privilege permissions. |
| 2 | Implement Azure Key Vault integration for all secrets | Done | `infra/terraform/main.tf`, `infra/kubernetes/secret-provider-class.yaml`, `infra/kubernetes/service-account.yaml`, `infra/kubernetes/deployment.yaml`, `apps/api-gateway/helm/templates/secretproviderclass.yaml`, `apps/api-gateway/helm/values.yaml`. |
| 3 | Add non-root users to all Dockerfiles | Done | Dockerfiles under `agents/`, `apps/`, `connectors/`, `services/` updated with non-root user. |
| 4 | Fix web console authentication bypass | Done | `apps/web/src/main.py` enforces JWKS-based token verification. |
| 5 | Disable ACR admin user in IaC | Done | `infra/terraform/main.tf` sets `admin_enabled = false`. |
| 6 | Mask PII in lineage data | Done | `packages/security/src/security/lineage.py`, `services/data-sync-service/src/main.py`, `tests/security/test_lineage_masking.py`. |
| 7 | Upgrade PostgreSQL to production-grade SKU + HA + TLS | Done | `infra/terraform/main.tf` PostgreSQL SKU, HA, TLS config, backups. |
| 8 | Fix Redis capacity configuration | Done | `infra/terraform/main.tf` Redis SKU/capacity + persistence settings. |
| 9 | Enable geo-redundant backups/storage + align RTO/RPO | Done | `infra/terraform/main.tf` backup/GRS settings, `docs/runbooks/disaster-recovery.md` RTO/RPO. |
| 10 | Fix Kubernetes image pull configuration | Done | `infra/kubernetes/deployment.yaml` removed ACR admin pull secret. |
| 11 | Add database foreign key constraints in migrations | Done | `data/migrations/versions/0001_create_core_tables.py`. |
| 47 | Add NSGs and enforce network isolation | Done | `infra/terraform/main.tf` VNet, subnet, NSG, rules. |
| 48 | Configure private endpoints + private DNS zones | Done | `infra/terraform/main.tf` private endpoints and DNS zones. |
| 49 | Add PodDisruptionBudgets for all deployables | Done | Helm `pdb.yaml` templates across app/service charts. |
| 50 | Add liveness probes to all Helm charts | Done | Helm deployment templates/values in app/service charts. |
| 51 | Enforce SSL/TLS across services | Done | `infra/terraform/main.tf` TLS minima + `ingress.yaml` templates with TLS. |
| 55 | Enforce HTTPS-only access on storage services | Done | `infra/terraform/main.tf` storage HTTPS-only + TLS min. |
| 56 | Add automated vulnerability scanning to CI | Done | `.github/workflows/security-scan.yml`, `.github/workflows/secret-scan.yml`, `.github/workflows/ci.yml`. |
| 12 | Add input validation to all schemas (JSON Schema + runtime validation at API boundaries) | Done | `services/policy-engine/src/main.py`, `apps/workflow-engine/src/main.py`, `connectors/sdk/src/runtime.py`, `agents/runtime/prompts/prompt_registry.py`, `apps/connector-hub/sandbox_registry.py`, `apps/analytics-service/job_registry.py`, `services/audit-log/src/main.py`. |
| 13 | Add unique constraints to database migrations | Done | `data/migrations/versions/0001_create_core_tables.py`. |
| 14 | Fix and expand data quality rules (make them real, executable, tested) | Done | `packages/data-quality/src/data_quality/rules.py`, `tests/test_data_quality_rules.py`. |
| 15 | Implement missing test fixtures (deterministic fixtures for connectors/services/agents) | Done | `connectors/*/tests/fixtures/projects.json`, `tests/conftest.py`. |
| 16 | Add coverage gates to CI; target >= 80% automated coverage | Done | `.github/workflows/ci.yml`. |
| 57 | Implement automated data retention enforcement (jobs/policies + tests) | Done | `services/audit-log/src/retention_job.py`, `services/audit-log/src/audit_storage.py`, `services/audit-log/tests/test_retention_job.py`. |
| 58 | Add audit trail verification tests (prove audit events emitted and persisted immutably) | Done | `services/audit-log/tests/test_audit_log.py`. |
| 59 | Complete DPIA documentation with actual system details | Done | `docs/compliance/privacy-dpia.md`. |
| 60 | Implement backup and recovery procedures (docs + automated checks/tests where possible) | Done | `docs/runbooks/backup-recovery.md`, `tests/test_backup_runbook.py`. |
| 74 | Coverage gate >= 80% automated coverage | Done | `.github/workflows/ci.yml`. |
