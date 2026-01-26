# Production Readiness Program Tracker

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Fix promotion workflow injection vulnerability in GitHub Actions | Done | `.github/workflows/promotion.yml` input validation, ref restriction, least-privilege permissions. |
| 2 | Implement Azure Key Vault integration for all secrets | Done | `infra/terraform/main.tf`, `infra/kubernetes/secret-provider-class.yaml`, `infra/kubernetes/service-account.yaml`, `infra/kubernetes/deployment.yaml`, `apps/api-gateway/helm/templates/secretproviderclass.yaml`, `apps/api-gateway/helm/values.yaml`. |
| 3 | Add non-root users to all Dockerfiles | Done | Dockerfiles under `agents/`, `apps/`, `connectors/`, `services/` updated with non-root user. |
| 4 | Fix web console authentication bypass | Done | `apps/web/src/main.py` enforces JWKS-based token verification. |
| 5 | Disable ACR admin user in IaC | Done | `infra/terraform/main.tf` sets `admin_enabled = false`. |
| 6 | Mask PII in lineage data | Done | `packages/security/src/security/lineage.py`, `services/data-sync-service/src/main.py`, `tests/security/test_lineage_masking.py`. |
| 56 | Add automated vulnerability scanning to CI | Done | `.github/workflows/security-scan.yml`, `.github/workflows/secret-scan.yml`, `.github/workflows/ci.yml`. |
