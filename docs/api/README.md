# API Reference

> Comprehensive reference for authentication, event contracts, governance rules, and webhook conventions across all platform services.

## Contents

- [Authentication](#authentication)
- [Event Contracts](#event-contracts)
- [API Governance](#api-governance)
- [Webhooks](#webhooks)

---

## Authentication

### Authentication model

All non-health endpoints require a **JWT bearer token**. The platform supports multiple token validation strategies:

- **JWT bearer tokens** — required for all protected endpoints via `Authorization: Bearer <token>`.
- **Tenant headers** — `X-Tenant-ID` must be present and match the tenant claim in the JWT.
- **Identity Access service** — when `IDENTITY_ACCESS_URL` is set, tokens are validated via `POST /v1/auth/validate` on the `services/identity-access` service.
- **Direct JWT validation** — supported via `IDENTITY_JWKS_URL` (public JWKS endpoint) or `IDENTITY_JWT_SECRET` (HMAC shared secret).
- **OIDC discovery** — supported via `IDENTITY_OIDC_DISCOVERY_URL` or `IDENTITY_ISSUER`; the platform fetches `.well-known/openid-configuration` and resolves the JWKS URI automatically.
- **Web console OIDC** — browser sessions use `/login` + `/oidc/callback` to establish a tenant-aware, httpOnly session cookie.
- **SCIM provisioning** — requires `Authorization: Bearer <SCIM_SERVICE_TOKEN>` and `X-Tenant-ID` for tenant isolation.

### Authorization model

| Mechanism | Description |
| --- | --- |
| RBAC enforcement | Roles and permissions are defined in `ops/config/rbac/roles.yaml` and `ops/config/rbac/permissions.yaml`. |
| Classification-based checks | Requests with a `classification` field are validated against allowed roles and field-level rules in `ops/config/rbac/field-level.yaml`. |
| Policy engine (optional) | When `POLICY_ENGINE_URL` is set, authorization decisions are delegated to the Policy Engine service. |
| ABAC evaluation | When `ABAC_ENFORCEMENT=true`, the gateway evaluates attribute-based policies via `POST /v1/abac/evaluate` or from local policies in `ops/config/abac/policies.yaml`. |
| Field masking | JSON responses are redacted according to `ops/config/rbac/field-level.yaml`, including nested fields expressed in dot notation. |

### Local development mode

Set `AUTH_DEV_MODE=true` to bypass live token validation during local development. The following variables control the synthetic identity:

| Variable | Default | Description |
| --- | --- | --- |
| `AUTH_DEV_TENANT_ID` | `dev-tenant` | Tenant identifier injected into requests. |
| `AUTH_DEV_ROLES` | `tenant_owner` | Role(s) assigned to the synthetic principal. |

### SAML federation (identity-access)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/v1/auth/saml/metadata` | GET | Returns SP metadata XML for IdP registration. |
| `/v1/auth/saml/login` | GET | Initiates the SAML login flow and redirects to the IdP. |
| `/v1/auth/saml/acs` | POST | Assertion consumer service — validates the SAML response and issues a JWT on success. |

Required environment variables:

| Variable | Required | Description |
| --- | --- | --- |
| `SAML_IDP_ENTITY_ID` | Yes | Entity ID of the identity provider. |
| `SAML_IDP_SSO_URL` | Yes | SSO endpoint URL of the identity provider. |
| `SAML_IDP_X509_CERT` | Yes | X.509 certificate of the identity provider. |
| `SAML_SP_ENTITY_ID` | Yes | Entity ID of this service provider. |
| `SAML_SP_ACS_URL` | Yes | Assertion consumer service URL. |
| `SAML_SP_SLS_URL` | No | Single logout service URL (defaults to ACS URL). |

### Web console OIDC endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/login` | GET | Redirects to the OIDC authorization endpoint and sets an httpOnly state cookie. |
| `/oidc/callback` | GET | Exchanges the authorization code for tokens, validates the ID token, and issues the session cookie. |
| `/session` | GET | Returns `{authenticated, subject, tenant_id, roles}` for the current browser session. |
| `/logout` | POST | Clears the session cookie and redirects to the IdP logout endpoint when available. |

Required configuration for the web console:

| Variable | Description |
| --- | --- |
| `OIDC_ISSUER_URL` | OIDC issuer base URL. |
| `OIDC_CLIENT_ID` | Registered client identifier. |
| `OIDC_CLIENT_SECRET` | Client secret (env or file reference). |
| `OIDC_REDIRECT_URI` | Registered redirect URI matching `/oidc/callback`. |
| `OIDC_TENANT_CLAIM` | JWT claim carrying the tenant ID (default: `tenant_id`). |
| `OIDC_ROLES_CLAIM` | JWT claim carrying the user's roles (default: `roles`). |
| `AUTH_SESSION_SIGNING_KEY` | Key used to sign the browser session cookie (env or file reference). |

Gateway configuration for IdP integration and ABAC:

| Variable | Description |
| --- | --- |
| `IDENTITY_OIDC_DISCOVERY_URL` | Optional explicit OIDC discovery URL. |
| `IDENTITY_ISSUER` | Issuer URL used for OIDC discovery when the above is unset. |
| `IDENTITY_TENANT_CLAIM` | Claim name for tenant ID (default: `tenant_id`). |
| `IDENTITY_ROLES_CLAIM` | Claim name for roles; supports dot notation and space-delimited values (default: `roles`). |
| `ABAC_ENFORCEMENT` | Set to `true` to enforce ABAC policy decisions. |
| `ABAC_POLICY_PATH` | Optional override for the local ABAC policy file path. |

### SCIM v2 provisioning (identity-access)

Base path: `/scim/v2`

Authentication requires both headers on every request:

```
Authorization: Bearer <SCIM_SERVICE_TOKEN>
X-Tenant-ID: <tenant-id>
```

Available endpoints:

| Endpoint | Description |
| --- | --- |
| `POST /Users` | Create a new user. |
| `GET /Users?filter=userName eq "user@company.com"` | Search users by filter. |
| `GET /Users/{id}` | Retrieve a specific user. |
| `PATCH /Users/{id}` | Update a specific user. |
| `POST /Groups` | Create a new group. |
| `GET /Groups` | List groups. |
| `PATCH /Groups/{id}` | Update a specific group. |
| `GET /scim/internal/roles/{user_id}` | Returns role mappings derived from the user's SCIM groups. |

### Implementation status

| Feature | Status |
| --- | --- |
| JWT validation and tenant header enforcement | Implemented |
| RBAC checks and optional policy engine integration | Implemented |
| OIDC login flow for the web console | Implemented |
| SCIM v2 provisioning | Implemented |
| SAML federation broker (metadata, login redirect, ACS) | Implemented |

### Verification steps

Inspect the API gateway authentication middleware:

```bash
rg -n "AuthTenantMiddleware" apps/api-gateway/src/api/middleware/security.py
```

Review the identity-access token validation endpoint:

```bash
rg -n "auth/validate" services/identity-access/src/main.py
```

Review SCIM v2 endpoints:

```bash
rg -n "scim/v2" services/identity-access/src/main.py
```

### Related documentation

- Security Architecture
- Tenancy Architecture

---

## Event Contracts

Inter-agent and inter-service communication uses a shared event envelope with domain-specific payloads. All payloads are JSON objects.

### Envelope

Every event — regardless of domain — shares the following top-level fields:

| Field | Type | Description |
| --- | --- | --- |
| `event_name` | string | Topic name (e.g. `demand.created`). |
| `event_id` | string | Unique event identifier. |
| `timestamp` | RFC3339 datetime | Event creation time. |
| `tenant_id` | string | Tenant identifier. |
| `payload` | object | Event-specific payload (see domain events below). |
| `correlation_id` | string | Cross-service correlation identifier. |
| `trace_id` | string | OpenTelemetry trace identifier. |

### Domain events

#### `demand.created`

Emitted when a new demand record is submitted.

| Field | Type | Description |
| --- | --- | --- |
| `demand_id` | string | Demand record identifier. |
| `source` | string | Intake source (e.g. CRM, portal). |
| `title` | string | Demand title. |
| `submitted_by` | string | Actor who submitted the demand. |
| `submitted_at` | RFC3339 datetime | Submission timestamp. |

#### `business_case.created`

Emitted when a business case is created for a demand.

| Field | Type | Description |
| --- | --- | --- |
| `business_case_id` | string | Business case identifier. |
| `demand_id` | string | Related demand record. |
| `project_name` | string | Proposed project name. |
| `created_at` | RFC3339 datetime | Creation timestamp. |
| `owner` | string | Business case owner. |

#### `portfolio.prioritized`

Emitted when a portfolio prioritization cycle completes.

| Field | Type | Description |
| --- | --- | --- |
| `portfolio_id` | string | Portfolio identifier. |
| `cycle` | string | Planning cycle label. |
| `prioritized_at` | RFC3339 datetime | Prioritization timestamp. |
| `ranked_projects` | array[string] | Ordered list of project IDs by priority. |

#### `program.created`

Emitted when a new program is established.

| Field | Type | Description |
| --- | --- | --- |
| `program_id` | string | Program identifier. |
| `name` | string | Program name. |
| `portfolio_id` | string | Associated portfolio. |
| `created_at` | RFC3339 datetime | Creation timestamp. |
| `owner` | string | Program owner. |

#### `charter.created`

Emitted when a project charter is created.

| Field | Type | Description |
| --- | --- | --- |
| `charter_id` | string | Charter identifier. |
| `project_id` | string | Project identifier. |
| `created_at` | RFC3339 datetime | Creation timestamp. |
| `owner` | string | Charter owner. |

#### `wbs.created`

Emitted when a work breakdown structure is established.

| Field | Type | Description |
| --- | --- | --- |
| `wbs_id` | string | Work breakdown structure identifier. |
| `project_id` | string | Project identifier. |
| `created_at` | RFC3339 datetime | Creation timestamp. |
| `baseline_date` | RFC3339 datetime | Optional baseline date. |

#### `project.transitioned`

Emitted when a project moves between lifecycle stages.

| Field | Type | Description |
| --- | --- | --- |
| `project_id` | string | Project identifier. |
| `from_stage` | string | Previous lifecycle stage. |
| `to_stage` | string | New lifecycle stage. |
| `transitioned_at` | RFC3339 datetime | Transition timestamp. |
| `actor_id` | string | Actor who initiated the transition. |

#### `schedule.baseline.locked`

Emitted when a schedule baseline is locked.

| Field | Type | Description |
| --- | --- | --- |
| `project_id` | string | Project identifier. |
| `schedule_id` | string | Schedule identifier. |
| `locked_at` | RFC3339 datetime | Baseline lock timestamp. |
| `baseline_version` | string | Baseline version label. |

#### `schedule.delay`

Emitted when a schedule delay is detected.

| Field | Type | Description |
| --- | --- | --- |
| `project_id` | string | Project identifier. |
| `schedule_id` | string | Schedule identifier. |
| `delay_days` | integer | Number of delayed days. |
| `reason` | string | Human-readable delay reason. |
| `detected_at` | RFC3339 datetime | Detection timestamp. |

#### `approval.created`

Emitted when an approval request is created.

| Field | Type | Description |
| --- | --- | --- |
| `approval_id` | string | Approval identifier. |
| `resource_type` | string | Type of resource requiring approval. |
| `resource_id` | string | Resource identifier. |
| `stage` | string | Stage gate or approval stage label. |
| `created_at` | RFC3339 datetime | Creation timestamp. |

#### `approval.decision`

Emitted when an approver records a decision.

| Field | Type | Description |
| --- | --- | --- |
| `approval_id` | string | Approval identifier. |
| `decision` | string | `approved`, `rejected`, or `deferred`. |
| `decided_at` | RFC3339 datetime | Decision timestamp. |
| `approver_id` | string | Approver identifier. |
| `comments` | string | Optional decision notes. |

#### `audit.*`

Audit events reuse the canonical audit schema defined in `data/schemas/audit-event.schema.json`. The envelope `event_name` must start with `audit.` (e.g. `audit.agent.policy`), and the `payload` must conform to the audit-event schema.

### Versioning rules

- Payload changes within a major version must remain backward compatible.
- Adding new optional fields does not require a version bump.
- Breaking changes must use a new event name suffix or increment the major version in payload metadata.

---

## API Governance

All FastAPI services under `services/` and `apps/` share a single API contract enforced across the platform.

### Versioning

- All public service routes are versioned under `/v1`.
- Every service exposes `GET /version` returning the following fields:

| Field | Description |
| --- | --- |
| `service` | Service name. |
| `version` | Semantic version of the deployed service. |
| `api_version` | API version string (e.g. `v1`). |
| `build_sha` | Git commit SHA of the build. |

- All responses include the `X-API-Version` header.

### Health endpoints

Every service exposes `GET /healthz` (some also expose `/health`) returning at minimum:

```json
{
  "status": "ok",
  "service": "<service-name>"
}
```

### Error envelope

All error responses must conform to the following shape:

```json
{
  "error": {
    "message": "Human-readable error description",
    "code": "machine_readable_code",
    "details": {},
    "correlation_id": "..."
  }
}
```

- `details` is optional and may be omitted when not applicable.
- `correlation_id` is included when available and is also returned via the `X-Correlation-ID` response header.

### Required request headers

| Header | Description |
| --- | --- |
| `Authorization: Bearer <token>` | JWT bearer token for authenticated requests. |
| `X-Tenant-ID: <tenant-id>` | Tenant identifier; must match the tenant claim in the JWT. |

### Correlation IDs

- An inbound `X-Correlation-ID` header is propagated through the entire request chain.
- If the header is absent, the service generates a new correlation ID for the request.
- The correlation ID is returned in both the `X-Correlation-ID` response header and the error envelope.

### Pagination headers

Collection endpoints must emit the following headers:

| Header | Description |
| --- | --- |
| `X-Page` | Current page number. |
| `X-Page-Size` | Number of items per page. |
| `X-Total-Count` | Total number of items across all pages. |
| `Link` | Navigation links (present when next or previous pages are available). |

---

## Webhooks

### Overview

Webhook endpoints are available for supported connectors. When webhooks are not configured or not supported by a connector, the platform falls back to polling and explicit sync requests via `POST /v1/sync/run` on the Data Sync Service.

### Endpoint

```
POST /v1/connectors/{connector_id}/webhook
```

Accepts JSON payloads from external systems. Webhook delivery is only accepted when the target connector is in an enabled state.

### Authentication and signature verification

Every inbound webhook request must include one of the following:

| Method | Header | Description |
| --- | --- | --- |
| Shared secret | `X-Webhook-Secret` | A plain shared secret configured in the API gateway via `CONNECTOR_<CONNECTOR_ID>_WEBHOOK_SECRET`. |
| HMAC signature | `X-Webhook-Signature` | An HMAC SHA-256 signature of the raw request body, formatted as `sha256=<hex_digest>`. |

Requests that include neither a valid secret nor a valid signature are rejected with a `401` response.

### Request headers

| Header | Required | Description |
| --- | --- | --- |
| `X-Webhook-Secret` | Conditional | Shared secret for direct comparison. |
| `X-Webhook-Signature` | Conditional | HMAC SHA-256 signature for payload integrity verification. |
| `X-Tenant-ID` | No | Tenant identifier used for audit logging. |

### Example request

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: $CONNECTOR_JIRA_WEBHOOK_SECRET" \
  -d '{"webhookEvent": "jira:issue_updated", "issue": {"key": "ENG-42"}}' \
  https://api.example.com/v1/connectors/jira/webhook
```

### Registration workflow

When a connector is activated, the API gateway attempts to register the webhook endpoint with the external service (provided the connector implements a registration handler). The URL registered with the external service takes the form:

```
{base_url}/v1/connectors/{connector_id}/webhook
```

If a connector does not support webhooks or no secret has been configured, polling remains the active fallback mechanism.

### Verification steps

Confirm the sync entry points available in the Data Sync Service:

```bash
rg -n "/v1/sync/run" services/data-sync-service/src/main.py
```

### Related documentation

- Connector Overview
- Data Sync Failures Runbook
