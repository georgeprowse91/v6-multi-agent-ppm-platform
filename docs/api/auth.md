# API Authentication

## Purpose

Describe authentication and authorization flows for API consumers.

## Authentication model

- **JWT bearer tokens** are required for all non-health endpoints.
- **Tenant headers** (`X-Tenant-ID`) must be present and match the tenant claim in the JWT.
- **Identity Access service** (`services/identity-access`) can validate tokens via `/auth/validate` when `IDENTITY_ACCESS_URL` is set.
- **Direct JWT validation** is supported via `IDENTITY_JWKS_URL` (public JWKS) or `IDENTITY_JWT_SECRET` (HMAC).

## Authorization model

- **RBAC enforcement**: Roles and permissions are defined in `config/rbac/roles.yaml` and `config/rbac/permissions.yaml`.
- **Classification-based checks**: Requests with a `classification` field are validated against allowed roles and field-level rules in `config/rbac/field-level.yaml`.
- **Policy engine optional**: When `POLICY_ENGINE_URL` is set, authorization checks are delegated to the policy engine service.

## Local development mode

Set `AUTH_DEV_MODE=true` and use the following environment variables for deterministic local testing:

- `AUTH_DEV_TENANT_ID` (default: `dev-tenant`)
- `AUTH_DEV_ROLES` (default: `tenant_owner`)

## Verification steps

- Inspect API gateway auth middleware:
  ```bash
  rg -n "AuthTenantMiddleware" apps/api-gateway/src/api/middleware/security.py
  ```
- Review identity access validation endpoint:
  ```bash
  rg -n "auth/validate" services/identity-access/src/main.py
  ```

## Implementation status

- **Implemented:** JWT validation, tenant header enforcement, RBAC checks, optional policy engine integration.
- **Planned:** SAML/OIDC federation brokers and SCIM-based user provisioning.

## Related docs

- [Security Architecture](../architecture/security-architecture.md)
- [Tenancy Architecture](../architecture/tenancy-architecture.md)
