# Policy Engine

The policy engine evaluates policy bundles and returns allow/deny decisions with reasons. It loads
the default policy bundle in dev mode and can be pointed at other bundles via configuration.

## Contracts

- OpenAPI: `services/policy-engine/contracts/openapi.yaml`
- Policy bundles: `services/policy-engine/policies/`

## Run locally

```bash
python -m tools.component_runner run --type service --name policy-engine
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `POLICY_BUNDLE_PATH` | `services/policy-engine/policies/bundles/default-policy-bundle.yaml` | Bundle used for evaluation |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `PORT` | `8080` | HTTP port for the service |

## Example request

```bash
curl -X POST http://localhost:8080/policies/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "bundle": {
      "apiVersion": "ppm.policies/v1",
      "kind": "PolicyBundle",
      "metadata": {"name": "demo", "version": "1.0.0", "owner": "qa"},
      "policies": []
    }
  }'
```

## Tests

```bash
pytest services/policy-engine/tests
```
