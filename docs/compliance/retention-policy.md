# Retention Policy

## Purpose

Document retention requirements for platform data, including audit logs and document records.

## Policy sources

Retention policies are defined in `config/retention/policies.yaml` and referenced by data classification levels in `config/data-classification/levels.yaml`.

## Current policy set

| Policy ID | Description | Duration (days) | Storage class |
| --- | --- | --- | --- |
| public-30d | Public data retained for 30 days | 30 | cool |
| internal-1y | Internal data retained for 1 year | 365 | cool |
| confidential-5y | Confidential data retained for 5 years | 1825 | archive |
| restricted-7y | Restricted data retained for 7 years | 2555 | archive |

## Enforcement points

- **Audit log service:** Applies retention policies based on classification and writes to immutable storage (`services/audit-log/src/audit_storage.py`).
- **Document service:** Evaluates retention rules using document policies (`apps/document-service/src/document_policy.py`).
- **Runbook verification:** Backup and recovery runbooks include retention validation steps.

## Operational guidance

1. Update policy durations in `config/retention/policies.yaml` to align with client requirements.
2. Update classification mappings in `config/data-classification/levels.yaml` if policies change.
3. Rotate storage classes in cloud environments to match required durability tiers.

## Verification steps

- Inspect retention policies:
  ```bash
  sed -n '1,160p' config/retention/policies.yaml
  ```
- Confirm audit log service loads retention policies:
  ```bash
  rg -n "RETENTION_CONFIG_PATH" services/audit-log/src/main.py
  ```

## Implementation status

- **Implemented:** Retention policies, audit log enforcement, document policy checks.
- **Planned:** Automated lifecycle management for non-audit data stores.

## Related docs

- [Data Classification](data-classification.md)
- [Backup & Recovery Runbook](../runbooks/backup-recovery.md)
