# Services

Supporting services that provide cross-cutting platform capabilities (audit logging, telemetry,
policy evaluation, identity access, data sync, and notifications). Each service ships its own Helm
chart, OpenAPI contract, and runnable MVP implementation.

## Quickstart

Validate all Helm charts:

```bash
python scripts/validate-helm-charts.py services
```

Validate the default policy bundle:

```bash
python scripts/validate-policies.py services/policy-engine/policies/bundles/default-policy-bundle.yaml
```

## How to verify

```bash
ls services
```

Expected output includes:

```text
audit-log
data-sync-service
identity-access
notification-service
policy-engine
telemetry-service
```

## Key files

- `services/*/contracts/`: OpenAPI contracts per service.
- `services/*/src/`: service runtime code.
- `services/*/tests/`: service smoke tests.
- `services/*/helm/`: Helm charts per service.
- `services/policy-engine/policies/`: policy bundles and rules.

## Example

Run the audit log service:

```bash
python -m tools.component_runner run --type service --name audit-log
```

## Next steps

- Extend service handlers with production integrations.
- Wire shared contracts via `packages/` as service APIs evolve.
