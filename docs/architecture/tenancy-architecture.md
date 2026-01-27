# Tenancy Architecture

## Purpose

Define the multi-tenancy model, tenant isolation boundaries, and configuration flows for the Multi-Agent PPM Platform.

## Architecture-level context

Tenant-aware routing is enforced at the API gateway and service layers. Each request includes a tenant identifier and is validated against configured identity and RBAC policies. Tenant configuration assets live under `config/tenants/`, while authorization policies and data classification rules live under `config/rbac/` and `config/data-classification/`.

## Tenant identification and request flow

- **Headers:** Every request to a tenant-aware service must include `X-Tenant-ID`. The API gateway middleware validates the tenant claim in the JWT and rejects mismatches. (`apps/api-gateway/src/api/middleware/security.py`).
- **Identity validation:** The gateway can validate JWTs locally using `IDENTITY_JWKS_URL` / `IDENTITY_JWT_SECRET` or delegate to the Identity Access service (`services/identity-access`).
- **Dev mode:** Local development can use `AUTH_DEV_MODE=true` with `AUTH_DEV_TENANT_ID` and `AUTH_DEV_ROLES` for deterministic testing.

## Data isolation approach

- **Logical isolation:** Tenant identifiers are persisted with records in workflow, analytics, audit, and document stores (`apps/workflow-engine/src/workflow_storage.py`, `apps/analytics-service/src/scheduler.py`, `services/audit-log/src/main.py`, `apps/document-service/src/main.py`).
- **Authorization enforcement:** RBAC and classification-based checks occur in the gateway (field masking and permission checks) and the policy engine (`services/policy-engine`).
- **Storage boundaries:** The default local stores use SQLite files scoped by service; for production deployments, replace local storage with environment-specific backing stores via Helm/Terraform configuration.

## Tenant configuration assets

| Asset | Path | Purpose |
| --- | --- | --- |
| Tenant defaults | `config/tenants/default.yaml` | Identity issuer, JWKS URL, and tenant metadata. |
| RBAC roles/permissions | `config/rbac/roles.yaml`, `config/rbac/permissions.yaml` | Roles and permissions used by middleware and policy engine. |
| Field-level rules | `config/rbac/field-level.yaml` | Classification and field masking rules. |
| Data classification | `config/data-classification/levels.yaml` | Classification levels and retention policy bindings. |

## Operational guidance

1. Create a tenant configuration file under `config/tenants/` for each deployment.
2. Configure identity settings in environment variables or tenant config (issuer, JWKS URL, audience).
3. Validate RBAC/field-level rules before onboarding users.
4. Ensure Helm chart values define per-environment secret references (Key Vault or other secret stores).

## Verification steps

- Inspect the tenant config:
  ```bash
  sed -n '1,120p' config/tenants/default.yaml
  ```
- Confirm API gateway tenant enforcement:
  ```bash
  rg -n "X-Tenant-ID" apps/api-gateway/src/api/middleware/security.py
  ```
- Validate workflow storage includes tenant IDs:
  ```bash
  rg -n "tenant_id" apps/workflow-engine/src/workflow_storage.py
  ```

## Implementation status

- **Implemented:** Tenant headers, JWT validation, RBAC enforcement, and tenant-scoped data records.
- **Planned:** Per-tenant infrastructure segmentation and automated tenant provisioning workflows.

## Related docs

- [Security Architecture](security-architecture.md)
- [RBAC/ABAC ADR](adr/0005-rbac-abac-field-level-security.md)
- [Data Classification](../compliance/data-classification.md)
