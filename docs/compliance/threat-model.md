# Threat Model – Multi-Agent PPM Platform

## Purpose

Document the security threat model for the Multi-Agent PPM Platform, focusing on the primary assets,
trust boundaries, and mitigations that protect tenant data, workflows, and audit trails.

## Scope

- API Gateway, Workflow Engine, orchestration layer, and core services.
- Data stores: Postgres, Redis, and immutable audit storage.
- External integrations: connectors to PPM/ERP/Collaboration systems.

## Assets

- Tenant data (projects, budgets, risks, workflows).
- Audit logs and lineage data.
- Identity data and access tokens.
- Configuration secrets and signing keys.

## Trust boundaries

1. **User to ingress** (public API boundary).
2. **Service-to-service communication** within the cluster.
3. **Service to data stores** (Postgres, Redis, blob/WORM storage).
4. **Connectors to external systems** (Jira, SAP, Workday, Teams, etc.).

## Threats & mitigations (STRIDE)

| Threat | Example scenario | Mitigations | Detection/Response |
| --- | --- | --- | --- |
| Spoofing | Forged JWT or tenant headers used to impersonate a user. | JWT validation, tenant middleware, SCIM-managed identities, MFA enforcement via IdP. | Auth error alerts, audit log correlation IDs, anomalous login alerts. |
| Tampering | Modification of audit events or workflow data. | WORM storage for audit logs, database integrity constraints, signed artifacts for releases. | Audit log immutability checks, DB integrity alerts. |
| Repudiation | Users deny actions taken in the system. | Immutable audit log entries, trace/correlation IDs, least-privilege roles. | Audit review reports, access log retention. |
| Information disclosure | Sensitive data exposed via misconfigured endpoints. | RBAC/ABAC policies, data classification, encryption in transit and at rest. | DLP alerts, config drift monitoring. |
| Denial of service | Flooding API or sync endpoints. | Rate limiting, autoscaling, queue backpressure, circuit breakers. | SLO alerts, throttling dashboards. |
| Elevation of privilege | Role escalation through misconfigured policies. | Policy engine validation, separation of duties, config reviews. | Policy evaluation logs, periodic access reviews. |

## High-risk areas & controls

1. **Connector integrations**
   - Risk: unauthorized data ingress or egress.
   - Controls: scoped credentials, per-connector allowlists, sync audit events.
2. **Audit log pipeline**
   - Risk: loss of compliance evidence.
   - Controls: WORM storage, retention enforcement, automated integrity checks.
3. **Policy enforcement**
   - Risk: inconsistent access decisions across services.
   - Controls: centralized policy engine, shared policy contracts, regression tests.

## Assumptions

- All services communicate over mTLS or private network paths.
- Secrets are stored in a managed vault (Key Vault).
- Production environments enforce least-privilege IAM policies.

## Residual risks

- Connector API changes can introduce unexpected data exposures.
- Misconfiguration risk remains if infrastructure-as-code review is bypassed.

## Review cadence

- Reassess before every major release or when a new external integration is introduced.
- Record results in `docs/production-readiness/evidence-pack.md`.
