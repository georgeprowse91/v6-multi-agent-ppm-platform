# Policy Package

Helpers intended for policy evaluation and policy bundle management.

## Current state

- No implementation code is present yet in `packages/policy/`.
- Policy bundles live under `services/policy-engine/policies/`.

## Quickstart

Inspect policy bundles used today:

```bash
ls services/policy-engine/policies/bundles
```

## How to verify

```bash
python scripts/validate-policies.py services/policy-engine/policies/bundles/default-policy-bundle.yaml
```

Expected output reports the bundle as valid.

## Key files

- `services/policy-engine/policies/`: current policy bundles.
- `packages/policy/README.md`: scope and next steps.

## Example

Search for policy IDs:

```bash
rg -n "id:" services/policy-engine/policies/bundles
```

## Next steps

- Add package sources under `packages/policy/src/`.
- Extract shared policy parsing utilities from `services/policy-engine/`.
