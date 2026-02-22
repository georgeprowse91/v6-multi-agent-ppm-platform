# Audit Evidence Guide

## Purpose

Enumerate auditable evidence sources and how to collect them for compliance reviews.

## Evidence categories

| Evidence type | Source | Validation steps |
| --- | --- | --- |
| Audit log events | `services/audit-log` storage | Query `/v1/audit/events/{id}` and verify retention metadata. |
| Retention policies | `ops/config/retention/policies.yaml` | Confirm retention durations and storage class. |
| Data classification | `ops/config/data-classification/levels.yaml` | Validate classification-to-retention mappings. |
| RBAC configuration | `ops/config/rbac/*.yaml` | Review roles, permissions, and field masking rules. |
| Infrastructure as code | `ops/infra/terraform/` | Validate Terraform plan/apply evidence. |
| Helm deployments | `apps/*/helm`, `services/*/helm` | Archive Helm release manifests. |
| CI/CD validation | `.github/workflows/*.yml` | Store CI logs for docs checks, linting, and tests. |

## Evidence collection workflow

1. **Audit log samples:** Pull a representative sample of audit events from the audit log service.
2. **Configuration snapshot:** Export the latest `ops/config/` directory for the tenant.
3. **Deployment evidence:** Save Terraform plans and Helm release manifests.
4. **CI logs:** Archive CI runs proving schema, manifest, and doc validation.

## Verification steps

- Confirm audit log service schema validation:
  ```bash
  rg -n "audit-event.schema.json" services/audit-log/src/main.py
  ```
- Validate the retention policy file exists:
  ```bash
  ls ops/config/retention/policies.yaml
  ```

## Implementation status

- **Implemented:** Audit log service, retention policies, RBAC configuration.
- **Implemented:** Automated evidence pack export via `/v1/audit/evidence/export` and web console trigger.

## Related docs

- [Audit Log ADR](../architecture/adr/0006-data-lineage-and-audit.md)
- [Security Architecture](../architecture/security-architecture.md)
