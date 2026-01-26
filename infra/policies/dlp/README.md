# DLP Policy Bundles

## Purpose
Data-loss-prevention (DLP) policies in this folder protect sensitive data handled by the platform.
They are referenced by infra compliance reviews and policy-engine evaluations.

## Responsibilities
- Define DLP rules for storage and data movement.
- Provide bundle metadata for audit and ownership tracking.
- Maintain schema-compliant YAML bundles.

## Folder structure
```
infra/policies/dlp/
├── README.md
├── bundles/
│   ├── default-dlp-policy-bundle.yaml
│   ├── pii.rego
│   └── credentials.rego
├── ../schema/policy-bundle.schema.json
└── ../README.md
```

## Conventions
- Bundle metadata scope should be `infra/dlp`.
- Use `dlp-###` policy IDs.
- Regex rules should be escaped for YAML string safety.

## How to add a new policy
1. Edit `bundles/default-dlp-policy-bundle.yaml` and add a new policy entry.
2. Ensure policy IDs remain unique.
3. Validate with `scripts/validate-policies.py`.

## How to validate/test
```bash
python scripts/validate-policies.py infra/policies/dlp/bundles/default-dlp-policy-bundle.yaml
```

The OPA/Rego bundles are exercised by `tests/policies/test_dlp_rego.py` and should be wired into the
policy-engine evaluation path for runtime enforcement.

## Example
```yaml
- id: dlp-001
  name: Block uploads with PAN
  description: Prevent storing unmasked payment card numbers.
  severity: critical
  enforcement: blocking
  rules:
    - field: content.regex
      operator: contains
      value: "\\b[0-9]{13,19}\\b"
```
