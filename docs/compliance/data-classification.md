# Data Classification

## Purpose

Define the platform's data classification levels and how they are enforced across services and storage.

## Classification levels

Classification levels are configured in `config/data-classification/levels.yaml` and map to retention policies and allowed roles.

| Level | Description | Retention policy ID | Allowed roles |
| --- | --- | --- | --- |
| public | Publicly shareable information | public-30d | tenant_owner, portfolio_admin, project_manager, analyst, auditor, integration_service |
| internal | Internal business data with limited exposure | internal-1y | tenant_owner, portfolio_admin, project_manager, analyst, auditor |
| confidential | Sensitive business data restricted to leadership | confidential-5y | tenant_owner, portfolio_admin, project_manager, auditor |
| restricted | Highly sensitive data | restricted-7y | tenant_owner, portfolio_admin |

## Enforcement points

- **API gateway:** Classification in request payloads is evaluated against RBAC rules; unauthorized roles receive masked fields (`apps/api-gateway/src/api/middleware/security.py`).
- **Audit log service:** Classification drives retention policy selection for audit events (`services/audit-log/src/main.py`).
- **Document service:** Classification is evaluated against document policies (`apps/document-service/src/document_policy.py`).

## Operational guidance

1. Update `config/data-classification/levels.yaml` to reflect customer policy.
2. Align `config/retention/policies.yaml` with classification retention requirements.
3. Validate RBAC role assignments in `config/rbac/roles.yaml` before onboarding users.

## Verification steps

- Inspect classification configuration:
  ```bash
  sed -n '1,160p' config/data-classification/levels.yaml
  ```
- Verify retention mapping is present:
  ```bash
  rg -n "retention_policy" config/data-classification/levels.yaml
  ```

## Implementation status

- **Implemented:** Classification config, RBAC enforcement, audit log retention mapping.
- **Planned:** Automated classification tagging for inbound connector data.

## Related docs

- [Retention Policy](retention-policy.md)
- [Security Architecture](../architecture/security-architecture.md)
- [Audit Evidence Guide](audit-evidence-guide.md)
