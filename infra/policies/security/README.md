# Security Policy Bundles

## Purpose
Security policy bundles define identity and access control requirements for the platform. They are
consumed by infrastructure compliance tooling and enforced by the policy engine.

## Responsibilities
- Capture identity, access, and privileged role controls.
- Keep policy ownership and versions up to date for audits.
- Provide schema-validated YAML bundles for enforcement.

## Folder structure
```
infra/policies/security/
├── README.md
├── bundles/
│   └── default-security-policy-bundle.yaml
├── ../schema/policy-bundle.schema.json
└── ../README.md
```

## Conventions
- Bundle scope must be `infra/security`.
- Use `sec-###` policy IDs.
- MFA-related policies should be `severity: critical` by default.

## How to add a new policy
1. Edit `bundles/default-security-policy-bundle.yaml` with a new policy entry.
2. Validate with `scripts/validate-policies.py`.
3. Update the `metadata.version` if the bundle is used in production.

## How to validate/test
```bash
python scripts/validate-policies.py infra/policies/security/bundles/default-security-policy-bundle.yaml
```

## Example
```yaml
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
