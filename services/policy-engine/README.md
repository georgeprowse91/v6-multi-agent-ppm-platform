# Policy Engine

Policy evaluation and compliance rule enforcement for the platform.

## Current state

- Policy bundles are stored under `services/policy-engine/policies/`.
- Helm chart exists under `services/policy-engine/helm/`.
- No runtime policy evaluation service yet.

## Quickstart

Validate the default policy bundle:

```bash
python scripts/validate-policies.py services/policy-engine/policies/bundles/default-policy-bundle.yaml
```

## How to verify

```bash
ls services/policy-engine/policies/bundles
```

Expected output includes the default policy bundle YAML.

## Key files

- `services/policy-engine/policies/`: policy bundles and rules.
- `services/policy-engine/helm/`: deployment assets.
- `services/policy-engine/src/`: service scaffolding.

## Example

List policy bundle IDs:

```bash
rg -n "id:" services/policy-engine/policies/bundles
```

## Next steps

- Implement evaluation APIs in `services/policy-engine/src/`.
- Integrate policy checks into `apps/api-gateway/src/api/routes/`.
