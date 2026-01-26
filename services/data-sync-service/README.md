# Data Sync Service

The data sync service plans connector reconciliation jobs and exposes a minimal HTTP trigger for
local development. In dev mode it reads YAML rule definitions and returns the planned sync actions.

## Contracts

- OpenAPI: `services/data-sync-service/contracts/openapi.yaml`
- Rule format: `services/data-sync-service/rules/*.yaml`

## Run locally

```bash
python -m tools.component_runner run --type service --name data-sync-service
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `DATA_SYNC_RULES_DIR` | `services/data-sync-service/rules` | Directory containing sync rule YAML files |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `PORT` | `8080` | HTTP port for the service |

## Example request

```bash
curl -X POST http://localhost:8080/sync/run \
  -H "Content-Type: application/json" \
  -d '{"connector": "jira", "dry_run": true}'
```

## Tests

```bash
pytest services/data-sync-service/tests
```
