# Production Security Baseline (Minimum Controls)

This baseline defines required controls for all platform services and maps each control to implementation anchors in the repository.

## Scope

- Service applications under `services/*/src/main.py`
- Shared security package in `packages/security/src/security/`
- Policy artifacts under `policies/` and `config/data-classification/`

## Required controls and code mappings

| Control area | Baseline requirement | Primary code locations |
| --- | --- | --- |
| Authentication | Protected routes must enforce tenant-aware auth middleware (`AuthTenantMiddleware`) with only `/healthz` and `/version` exempted; only designated identity/auth services may omit this middleware. | `packages/security/src/security/auth.py`, `services/data-service/src/main.py`, `services/data-sync-service/src/main.py`, `services/data-lineage-service/src/main.py`, `services/notification-service/src/main.py`, `services/realtime-coedit-service/src/main.py`, `services/policy-engine/src/main.py`, `services/telemetry-service/src/main.py`, `services/audit-log/src/main.py` |
| RBAC / ABAC | Authorization decisions must use policy-backed role/action/resource evaluation and ABAC condition checks. | `services/policy-engine/src/main.py`, `policies/rbac/roles.yaml`, `policies/abac/rules.yaml` |
| DLP / masking | Sensitive fields and lineage payloads must be masked/redacted before persistence or downstream emission, aligned to classification levels. | `services/data-lineage-service/src/main.py`, `services/data-sync-service/src/main.py`, `packages/security/src/security/lineage.py`, `config/data-classification/levels.yaml` |
| Secret resolution | Secret-like env vars (`*_SECRET`, `*_TOKEN`, `*_PASSWORD`, `*_KEY`, `*_CONNECTION_STRING`, `*_WEBHOOK`) must be resolved through `security.secrets.resolve_secret` and must not be consumed as raw plaintext from `os.getenv`. | `packages/security/src/security/secrets.py`, `services/auth-service/src/main.py`, `services/identity-access/src/main.py`, `services/notification-service/src/main.py`, `services/audit-log/src/audit_storage.py` |
| Security headers / API governance | Services must apply shared governance and headers middleware (`apply_api_governance`) and include request tracing/metrics middleware. | `packages/security/src/security/api_governance.py`, `packages/security/src/security/headers.py`, `services/*/src/main.py` |
| Auditability | Security-relevant flows must produce immutable audit evidence with retention enforcement and evidence export capability. | `services/audit-log/src/main.py`, `services/audit-log/src/audit_storage.py`, `data/schemas/audit-event.schema.json`, `config/retention/policies.yaml` |

## Automated enforcement

- `ops/tools/check_security_middleware.py` enforces security middleware presence and auth exempt-path policy.
- `ops/tools/check_secret_source_policy.py` enforces secret source policy (`resolve_secret` usage).
- `tests/security/test_security_baseline_compliance.py` provides a parameterized cross-service suite for baseline compliance.
- `make check-security-baseline` runs all baseline gates.
