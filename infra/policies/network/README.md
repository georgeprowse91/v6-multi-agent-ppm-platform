# Network Policy Bundles

## Purpose
Network policy bundles define ingress and service-mesh rules for the platform infrastructure.
They ensure services deploy with approved connectivity constraints.

## Responsibilities
- Capture baseline ingress and east-west traffic policies.
- Maintain versioned bundles owned by the networking team.
- Provide validated YAML bundles for enforcement.

## Folder structure
```
infra/policies/network/
├── README.md
├── bundles/
│   └── default-network-policy-bundle.yaml
├── ../schema/policy-bundle.schema.json
└── ../README.md
```

## Conventions
- Bundle scope must be `infra/network`.
- Use `net-###` policy IDs.
- Policies with `enforcement: blocking` should include explicit remediation guidance in descriptions.

## How to add a new policy
1. Add a new entry to `bundles/default-network-policy-bundle.yaml`.
2. Validate with `scripts/validate-policies.py`.
3. Document changes in the policy bundle metadata description.

## How to validate/test
```bash
python scripts/validate-policies.py infra/policies/network/bundles/default-network-policy-bundle.yaml
```

## Example
```yaml
- id: net-001
  name: Restrict public ingress
  description: Public ingress requires an approved service tag.
  severity: high
  enforcement: blocking
  rules:
    - field: ingress.is_public
      operator: equals
      value: true
```
