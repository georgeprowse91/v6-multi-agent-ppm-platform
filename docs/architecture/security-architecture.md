# Security Architecture

## Purpose

Describe how the platform protects data, enforces access controls, captures audit evidence, and satisfies compliance requirements.

## Architecture-level context

Security spans the identity plane (SSO), authorization plane (RBAC/ABAC), data protection (encryption, retention), and audit/monitoring. Security controls are documented in `docs/compliance/` and enforced by agents and infrastructure defined in `infra/`.

## Identity & authentication

- **SSO**: Azure AD / Okta via OIDC or SAML.
- **Service authentication**: managed identities or mTLS between internal services.
- **API tokens**: scoped tokens for external integrations.

## Authorization model (RBAC + ABAC)

- **RBAC**: role-based permissions for portfolios, programs, projects.
- **ABAC**: attribute-based policies (data classification, region, business unit).
- **Field-level controls**: sensitive fields masked for restricted roles.

## Audit events

Audit events are captured for:

- Stage-gate approvals
- Budget or scope changes
- Data synchronization activity
- Authentication and authorization decisions

Audit schema reference: `data/schemas/audit-event.schema.json`.

## Data protection and retention

- **Encryption**: TLS in transit; AES-256 at rest.
- **Secrets**: Azure Key Vault references in `config/`.
- **Retention**: see `docs/compliance/retention-policy.md` for standard schedules.
- **Privacy**: DPIA template in `docs/compliance/privacy-dpia-template.md`.

## Threat model summary

The threat model (see `docs/compliance/threat-model.md`) highlights the top risks:

- Connector credential leakage
- Unauthorized cross-tenant access
- LLM prompt injection
- Data exfiltration via integrations

Mitigations include secret rotation, tenant isolation, policy guardrails, and audit logging.

## Usage example

Open the audit event schema:

```bash
sed -n '1,120p' data/schemas/audit-event.schema.json
```

## How to verify

Check that compliance docs exist:

```bash
ls docs/compliance
```

Expected output includes `retention-policy.md` and `threat-model.md`.

## Implementation status

- **Implemented**: documentation, audit schema, retention and DPIA templates.
- **Implemented**: IAM role mapping with Azure AD group ingestion and automated policy enforcement via the policy engine.

## Related docs

- [Compliance Controls Mapping](../compliance/controls-mapping.md)
- [Retention Policy](../compliance/retention-policy.md)
- [Threat Model](../compliance/threat-model.md)
