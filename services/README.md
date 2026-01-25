# Services

Supporting services that provide cross-cutting platform capabilities (audit logging, telemetry,
policy evaluation, and notifications). Each service ships its own Helm chart and skeleton code.

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

- `services/*/helm/`: Helm charts per service.
- `services/*/src/`: service code scaffolding.
- `services/policy-engine/policies/`: policy bundles and rules.

## Example

```bash
ls services/audit-log/helm
```

Expected output includes `Chart.yaml` and `values.yaml`.

## Next steps

- Implement service handlers under each `services/*/src/` folder.
- Wire shared contracts via `packages/` once service APIs are defined.
