# API Governance Rules

The platform uses one shared API contract for every FastAPI service under `services/*` and `apps/*`.

## Versioning

- Public service routes are versioned under `/v1`.
- Services expose `GET /version` returning:
  - `service`
  - `version`
  - `api_version`
  - `build_sha`
- Responses include `X-API-Version`.

## Health

- Services expose `GET /healthz` (and optional `/health`) with `status` and `service` keys.

## Error envelope

Errors must return this shape:

```json
{
  "error": {
    "message": "Human-readable error",
    "code": "machine_readable_code",
    "details": {},
    "correlation_id": "..."
  }
}
```

- `details` is optional.
- `correlation_id` is present when available and also returned via `X-Correlation-ID` header.

## Auth headers

- `Authorization: Bearer <token>`
- `X-Tenant-ID: <tenant-id>`

## Correlation IDs

- Inbound `X-Correlation-ID` is propagated.
- If absent, the service generates one.
- The value is returned in both headers and error envelopes.

## Pagination headers

Collection endpoints should emit:

- `X-Page`
- `X-Page-Size`
- `X-Total-Count`
- `Link` (when next/prev navigation is available)
