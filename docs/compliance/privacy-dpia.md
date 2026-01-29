# Privacy DPIA – Multi-Agent PPM Platform

## 1. Project overview

**System name:** Multi-Agent PPM Platform

**Purpose:** Provide portfolio, program, project, budget, and risk management with multi-agent orchestration, audit logging, and policy enforcement.

**Deployment model:** Azure Kubernetes Service (AKS) with managed Postgres, Redis, and Blob Storage. Infrastructure is defined in Terraform (`infra/terraform/main.tf`).

## 2. Data processing summary

### 2.1 Data subjects
- Internal employees (portfolio managers, project managers, auditors, administrators).
- External partners (vendors) where vendor contacts are stored.

### 2.2 Categories of personal data
- **Identifiers:** user IDs, tenant IDs, role assignments, audit actor IDs.
- **Contact data (limited):** vendor owner or contact names.
- **Operational metadata:** access tokens (validated only, not persisted), request metadata (trace/correlation IDs).

### 2.3 Special category data
- None processed by design. Classification controls restrict sensitive payloads at ingestion and in audit events.

### 2.4 Data flows
1. API Gateway receives user requests and forwards to services.
2. Domain services persist business data (projects, budgets, risks) to Postgres.
3. Audit Log service writes immutable events to WORM storage with retention metadata.
4. Analytics jobs read curated datasets and emit aggregated metrics.

### 2.5 Data storage locations
- **Relational data:** Azure Database for PostgreSQL (geo-redundant backups enabled).
- **Audit logs:** Azure Blob Storage with immutability policies (or encrypted local WORM storage for dev).
- **Configuration:** Azure Key Vault for secrets and Kubernetes ConfigMaps for non-secret settings.

## 3. Lawful basis and purpose limitation

- Processing is required to deliver contracted portfolio management services (contractual necessity).
- Audit logging supports security and compliance obligations (legitimate interests).
- Data is used only for operational, compliance, and reporting purposes; no advertising or secondary use.

## 4. Data minimization and retention

- Only required identifiers, role data, and operational metadata are stored.
- Retention policies are enforced per classification (`config/retention/policies.yaml`) with automated pruning.
- Audit events include `retention_policy` and `retention_until` fields to enforce deletion after expiry.

## 5. Security measures

- Authentication and tenant isolation enforced by `AuthTenantMiddleware`.
- Audit log events are stored in encrypted, write-once storage with immutability checks.
- Secrets stored in Azure Key Vault; no secrets embedded in code or configs.
- TLS enforced for service ingress and managed databases.

## 6. Data subject rights support

- Requests for access, correction, or deletion are handled through tenant administrators.
- Audit logs remain immutable, but access to events is restricted via role-based access controls.
- Deletion requests trigger downstream deletions and retention enforcement where legally permitted.

## 7. Risk assessment

| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| Unauthorized tenant data access | High | Low | JWT verification, tenant scoping middleware, RBAC policy checks. |
| Audit log tampering | High | Low | WORM storage, encryption, immutability enforcement tests. |
| Over-retention of data | Medium | Low | Automated retention enforcement and tests. |
| Data loss | High | Low | Geo-redundant backups, recovery runbooks, restore drills. |

## 8. DPIA outcome

Residual risk is **low** after applying access controls, encryption, retention enforcement, and audit logging. The platform may process additional personal data only after updating this DPIA and performing a privacy review. This DPIA is considered **complete** for the current release scope and is tied to release readiness sign-off.

## 9. Review cadence

- **Trigger events:** new integrations, new data categories, or changes to retention/encryption.
- **Scheduled review:** every 6 months or before major releases.
- **Evidence:** update `docs/production-readiness/evidence-pack.md` with review notes.

## 10. Approvals

| Role | Status | Evidence |
| --- | --- | --- |
| Data Protection Officer | Completed | Release readiness checklist |
| Security Lead | Completed | Release readiness checklist |
| Product Owner | Completed | Release readiness checklist |
