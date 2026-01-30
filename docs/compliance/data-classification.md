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
- **DLP scanning:** Document ingestion and connector payload logging are scanned for sensitive data. Findings are blocked or advisory based on `config/security/dlp-policies.yaml`.
- **Assistant prompt safety:** Assistant requests are sanitized for prompt-injection markers and blocked or warned before forwarding.
- **Encryption at rest:** Document content is encrypted in local storage using Fernet keys provided via secret references.

## Operational guidance

1. Update `config/data-classification/levels.yaml` to reflect customer policy.
2. Align `config/retention/policies.yaml` with classification retention requirements.
3. Validate RBAC role assignments in `config/rbac/roles.yaml` before onboarding users.
4. Ensure DLP policy thresholds in `config/security/dlp-policies.yaml` align to classification expectations.
5. Provide encryption keys via Key Vault / CSI or environment references (`DOCUMENT_ENCRYPTION_KEY`, `ARTIFACT_STORE_ENCRYPTION_KEY`).

## DLP enforcement rules

- **Documents:** Content and metadata are scanned on ingestion. Blocking findings return HTTP 403 with redacted reasons; advisory findings are returned in the response advisories list.
- **Connector SDK logging:** Request/response payloads are redacted before logging to prevent sensitive data leakage.
- **Assistant prompts:** Prompt-injection markers are removed from forwarded text, with warnings surfaced to the UI when advisory.

## Encryption at rest scope

- **Document service:** Document content is encrypted before persistence and decrypted on read operations.
- **Workspace artifacts:** Timeline notes, spreadsheet cell values, and tree notes are slated for encryption in a follow-on PR if schema changes are required.

## Key management & rotation

- Keys must be provided through secret references (`env:`, `file:`, or Key Vault CSI mounts). Keys are never generated in production.
- Rotate keys by provisioning a new key, re-encrypting stored documents offline, updating secret references, and restarting services with the new key.

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
- **Implemented:** Automated classification tagging in the connector ingestion pipeline.

## Related docs

- [Retention Policy](retention-policy.md)
- [Security Architecture](../architecture/security-architecture.md)
- [Audit Evidence Guide](audit-evidence-guide.md)
