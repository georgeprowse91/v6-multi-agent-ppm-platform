# ADR 0005: RBAC/ABAC and Field-Level Security

## Status

Accepted.

## Context

The platform serves multiple tenants and must enforce role-based permissions as well as classification-based field masking. These controls must work both with and without an external policy engine.

## Decision

Implement RBAC and classification-based field-level masking in the API gateway middleware using configuration under `config/rbac/`. When a policy engine is available (`POLICY_ENGINE_URL`), delegate authorization decisions to it; otherwise enforce locally using YAML configs.

## Consequences

- Default local enforcement ensures predictable behavior without external dependencies.
- Policy engine enables centralized authorization for production environments.
- Classification rules must remain synchronized with data-classification and retention policies.

## References

- `apps/api-gateway/src/api/middleware/security.py`
- `services/policy-engine/src/main.py`
- `config/rbac/roles.yaml`
- `config/rbac/field-level.yaml`
