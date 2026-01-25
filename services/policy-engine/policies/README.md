# Policy Engine Bundles

## Purpose
This folder stores policy bundles evaluated by the policy engine service. The default bundle path
is captured in `services/policy-engine/src/policy_config.py` and used as the baseline for
validating downstream service policy packs.

## Responsibilities
- Maintain platform-wide policy bundles used by the policy engine.
- Validate bundle schemas before deployment to avoid runtime enforcement errors.
- Track ownership and versioning for compliance reviews.

## Folder structure
```
services/policy-engine/policies/
├── README.md
├── bundles/
│   └── default-policy-bundle.yaml
└── schema/
    └── policy-bundle.schema.json
```

## Conventions
- Policy IDs should be prefixed with `pe-` for policy engine rules.
- `metadata.scope` is `policy-engine` for core evaluation bundles.
- Keep bundle versions aligned with policy-engine release versions.

## How to add a new policy bundle
1. Copy `bundles/default-policy-bundle.yaml` and update the `metadata` fields.
2. Add new policy rules with unique IDs.
3. Run validation locally and in CI.

## How to validate/test
```bash
python scripts/validate-policies.py services/policy-engine/policies/bundles/default-policy-bundle.yaml
```

## Example
```yaml
apiVersion: ppm.policies/v1
kind: PolicyBundle
metadata:
  name: policy-engine-default
  version: "1.0.0"
  owner: policy-platform
  scope: policy-engine
policies:
  - id: pe-001
    name: Enforce bundle versioning
    description: Require semantic versioning for bundle metadata.
    severity: medium
    enforcement: blocking
    rules:
      - field: metadata.version
        operator: contains
        value: "."
```
