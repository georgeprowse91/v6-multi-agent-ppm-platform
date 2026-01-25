# Connector Hub Sandbox

## Purpose
Sandbox configurations allow connector developers to test integrations locally using fixture
responses. The connector hub can read these configs to emulate upstream systems without making
live API calls. The sandbox registry lives in `apps/connector-hub/sandbox_registry.py`.

## Responsibilities
- Provide sandbox connector configurations for local testing.
- Store fixture responses used by simulated connector runs.
- Keep configs validated against the sandbox schema.

## Folder structure
```
apps/connector-hub/sandbox/
├── README.md
├── examples/
│   └── github-sandbox-connector.yaml
├── fixtures/
│   ├── issues.json
│   └── repo.json
└── schema/
    └── sandbox-connector.schema.json
```

## Conventions
- Use `apiVersion: ppm.connectors/v1` and `kind: ConnectorSandbox`.
- Keep fixture files under `fixtures/` and reference them in `sandbox.fixtures`.
- Store secrets in env vars referenced by `connector.auth.token_env`.

## How to add a new sandbox config
1. Copy `examples/github-sandbox-connector.yaml` and update connector metadata.
2. Add fixture JSON files under `fixtures/`.
3. Validate the config with the script below.
4. Confirm the new file is picked up by `apps/connector-hub/sandbox_registry.py`.

## How to validate/test
```bash
python scripts/validate-connector-sandbox.py apps/connector-hub/sandbox/examples/github-sandbox-connector.yaml
```

## Example
```yaml
apiVersion: ppm.connectors/v1
kind: ConnectorSandbox
metadata:
  name: github-sandbox
  owner: connector-hub
connector:
  type: github
  base_url: https://api.github.com
```
