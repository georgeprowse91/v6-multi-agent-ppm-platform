# Document Service Policies

## Purpose
Policy bundles in this folder define access controls, retention requirements, and validation rules
for the document service. The default bundle path is captured in
`apps/document-service/document_policy_config.py` for downstream services to consume.

## Responsibilities
- Capture document ingestion and retention rules for the document service.
- Maintain versioned policy bundles tied to document workflows.
- Provide schema-validated YAML bundles for policy evaluation.

## Folder structure
```
apps/document-service/policies/
├── README.md
├── bundles/
│   └── default-policy-bundle.yaml
└── schema/
    └── policy-bundle.schema.json
```

## Conventions
- Use `doc-###` policy IDs for document-specific rules.
- `metadata.scope` should be `document-service`.
- Bundle `metadata.version` must follow semantic versioning.

## How to add a new policy bundle
1. Duplicate `bundles/default-policy-bundle.yaml` and edit the metadata.
2. Add rules under `policies:` for new document constraints.
3. Run the validation script to ensure schema compliance.
4. Update `apps/document-service/document_policy_config.py` if the default bundle changes.

## How to validate/test
```bash
python scripts/validate-policies.py apps/document-service/policies/bundles/default-policy-bundle.yaml
```

## Example
```yaml
apiVersion: ppm.policies/v1
kind: PolicyBundle
metadata:
  name: document-default
  version: "1.0.0"
  owner: document-platform
  scope: document-service
policies:
  - id: doc-001
    name: Block uploads without classification
    description: Require classification for every document upload.
    severity: high
    enforcement: blocking
    rules:
      - field: document.classification
        operator: equals
        value: ""
```
