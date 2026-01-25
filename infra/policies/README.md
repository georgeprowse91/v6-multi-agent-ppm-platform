# Infrastructure Policy Bundles

## Purpose
The `infra/policies` tree stores platform infrastructure policy bundles used by compliance tooling
and platform reviews. Each domain folder (DLP, network, security) owns its own bundle and shares a
common schema.

## Responsibilities
- Maintain baseline infra policy bundles by domain.
- Keep schema definitions aligned with the policy engine format.
- Provide validated bundles for deployment and audit evidence.

## Folder structure
```
infra/policies/
├── schema/
│   └── policy-bundle.schema.json
├── dlp/
│   ├── README.md
│   └── bundles/default-dlp-policy-bundle.yaml
├── network/
│   ├── README.md
│   └── bundles/default-network-policy-bundle.yaml
└── security/
    ├── README.md
    └── bundles/default-security-policy-bundle.yaml
```

## Conventions
- Use `infra/<domain>` in `metadata.scope`.
- Bundle file names follow `default-<domain>-policy-bundle.yaml`.
- Policy IDs should be prefixed per domain (`dlp-`, `net-`, `sec-`).

## How to add a new policy domain
1. Create a new folder under `infra/policies/<domain>` with a `README.md`.
2. Add a bundle under `infra/policies/<domain>/bundles/` following the schema.
3. Validate with the script below and commit the new domain docs.

## How to validate/test
```bash
python scripts/validate-policies.py infra/policies/dlp/bundles/default-dlp-policy-bundle.yaml \
  infra/policies/network/bundles/default-network-policy-bundle.yaml \
  infra/policies/security/bundles/default-security-policy-bundle.yaml
```

## Example
```yaml
apiVersion: ppm.policies/v1
kind: PolicyBundle
metadata:
  name: infra-security-default
  version: "1.0.0"
  owner: infra-security
  scope: infra/security
policies:
  - id: sec-001
    name: Enforce MFA
    description: Users must have MFA enabled for admin roles.
    severity: critical
    enforcement: blocking
    rules:
      - field: identity.mfa_enabled
        operator: equals
        value: false
```
