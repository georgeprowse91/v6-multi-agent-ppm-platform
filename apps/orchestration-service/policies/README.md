# Orchestration Service Policies

## Purpose
Policy bundles in this folder drive the enforcement rules for the orchestration service. The
orchestrator loads the default bundle path defined in
`apps/orchestration-service/src/orchestrator.py` and uses the policies to gate routing and execution
logic.

## Responsibilities
- Define policy bundles that apply to orchestration routing decisions.
- Document policy ownership and versioning for compliance reviews.
- Provide validated, schema-backed YAML bundles for deployment.

## Folder structure
```
apps/orchestration-service/policies/
├── README.md
├── bundles/
│   └── default-policy-bundle.yaml
└── schema/
    └── policy-bundle.schema.json
```

## Conventions
- Bundles live under `bundles/` and use `apiVersion: ppm.policies/v1`.
- `metadata.name` should be unique per bundle and scoped to the service.
- Policy IDs must be unique within a bundle (`orch-###` recommended).

## How to add a new policy bundle
1. Copy `bundles/default-policy-bundle.yaml` and update `metadata` fields.
2. Add or edit policies under `policies:` using unique `id` values.
3. Validate the bundle using the script below.
4. Update `DEFAULT_POLICY_BUNDLE_PATH` in `apps/orchestration-service/src/orchestrator.py` if the
   default bundle changes.

## How to validate/test
```bash
python scripts/validate-policies.py apps/orchestration-service/policies/bundles/default-policy-bundle.yaml
```

## Example
```yaml
apiVersion: ppm.policies/v1
kind: PolicyBundle
metadata:
  name: orchestration-default
  version: "1.0.0"
  owner: platform-governance
  scope: orchestration-service
policies:
  - id: orch-001
    name: Block deprecated agent versions
    description: Prevent routing to agents marked as deprecated.
    severity: high
    enforcement: blocking
    rules:
      - field: agent.version_status
        operator: equals
        value: deprecated
```
