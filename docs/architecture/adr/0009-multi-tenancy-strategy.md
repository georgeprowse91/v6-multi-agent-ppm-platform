# ADR 0009: Multi-Tenancy Strategy

## Status

Accepted.

## Context

The platform serves multiple tenants and must enforce tenant isolation while keeping operational overhead manageable. A tenant identifier must flow through APIs and storage layers.

## Decision

Use logical multi-tenancy enforced by headers and JWT claims. Services persist a `tenant_id` attribute alongside records and validate that the calling tenant matches stored data. Tenant configuration is stored under `config/tenants/` and used to bootstrap identity settings.

## Consequences

- Services can share infrastructure while maintaining isolation in data models.
- All API clients must supply `X-Tenant-ID` headers.
- Strong isolation (separate databases per tenant) is deferred and can be introduced later.

## References

- `apps/api-gateway/src/api/middleware/security.py`
- `config/tenants/default.yaml`
- `docs/architecture/tenancy-architecture.md`
