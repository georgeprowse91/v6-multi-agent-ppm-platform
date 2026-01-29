# API Authentication

## Purpose

Describe authentication and authorization flows for API consumers.

## Authentication model

- **JWT bearer tokens** are required for all non-health endpoints.
- **Tenant headers** (`X-Tenant-ID`) must be present and match the tenant claim in the JWT.
- **Identity Access service** (`services/identity-access`) can validate tokens via `/auth/validate` when `IDENTITY_ACCESS_URL` is set.
- **Direct JWT validation** is supported via `IDENTITY_JWKS_URL` (public JWKS) or `IDENTITY_JWT_SECRET` (HMAC).
- **OIDC discovery** is supported via `IDENTITY_OIDC_DISCOVERY_URL` or `IDENTITY_ISSUER` (fetches `.well-known/openid-configuration` and JWKS).
- **Web console OIDC** uses `/login` + `/oidc/callback` to establish a tenant-aware session cookie.
- **SCIM provisioning** requires `Authorization: Bearer <SCIM_SERVICE_TOKEN>` and `X-Tenant-ID` for tenant isolation.

## Authorization model

- **RBAC enforcement**: Roles and permissions are defined in `config/rbac/roles.yaml` and `config/rbac/permissions.yaml`.
- **Classification-based checks**: Requests with a `classification` field are validated against allowed roles and field-level rules in `config/rbac/field-level.yaml`.
- **Policy engine optional**: When `POLICY_ENGINE_URL` is set, authorization checks are delegated to the policy engine service.
- **ABAC evaluation**: When `ABAC_ENFORCEMENT=true`, the gateway evaluates attribute-based policies using the policy engine (`/abac/evaluate`) or local policies in `config/abac/policies.yaml`.
- **Field masking**: JSON responses are redacted using `config/rbac/field-level.yaml`, including nested fields defined with dot notation.

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
- Review SCIM v2 endpoints:
  ```bash
  rg -n "scim/v2" services/identity-access/src/main.py
  ```

## Implementation status

- **Implemented:** JWT validation, tenant header enforcement, RBAC checks, optional policy engine integration.
- **Implemented:** OIDC login flow for the web console and SCIM v2 provisioning.
- **Planned:** SAML federation brokers.

## Web console OIDC endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/login` | GET | Redirects to the OIDC authorization endpoint and sets an httpOnly state cookie. |
| `/oidc/callback` | GET | Exchanges the auth code for tokens, validates the ID token, and issues the session cookie. |
| `/session` | GET | Returns `{authenticated, subject, tenant_id, roles}` for the current browser session. |
| `/logout` | POST | Clears the session cookie; redirects to the IdP logout endpoint when available. |

Required configuration (web):

- `OIDC_ISSUER_URL`
- `OIDC_CLIENT_ID`
- `OIDC_CLIENT_SECRET` (env/file reference)
- `OIDC_REDIRECT_URI`
- `OIDC_TENANT_CLAIM` (default `tenant_id`)
- `OIDC_ROLES_CLAIM` (default `roles`)
- `AUTH_SESSION_SIGNING_KEY` (env/file reference)

Gateway configuration for IdP/ABAC:

- `IDENTITY_OIDC_DISCOVERY_URL` (optional) or `IDENTITY_ISSUER` (issuer for OIDC discovery)
- `IDENTITY_TENANT_CLAIM` (default `tenant_id`)
- `IDENTITY_ROLES_CLAIM` (default `roles`, supports dot notation and space-delimited values)
- `ABAC_ENFORCEMENT` (set to `true` to enforce ABAC decisions)
- `ABAC_POLICY_PATH` (optional override for ABAC policy file)

## SCIM v2 provisioning (identity-access)

Base path: `/scim/v2`

Authentication:

- `Authorization: Bearer <SCIM_SERVICE_TOKEN>` (resolved via env/file reference)
- `X-Tenant-ID: <tenant-id>`

Endpoints:

- `POST /Users`
- `GET /Users?filter=userName eq "user@company.com"`
- `GET /Users/{id}`
- `PATCH /Users/{id}`
- `POST /Groups`
- `GET /Groups`
- `PATCH /Groups/{id}`
- `GET /scim/internal/roles/{user_id}` (returns role mappings derived from SCIM groups)

## Related docs

- [Security Architecture](../architecture/security-architecture.md)
- [Tenancy Architecture](../architecture/tenancy-architecture.md)
