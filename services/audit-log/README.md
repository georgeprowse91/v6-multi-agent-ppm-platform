# Audit Log Service

The audit log service captures and stores audit events for compliance, traceability, and security
reviews across the platform. It validates incoming events against the canonical audit-event schema
and persists them to a local JSONL store in dev mode.

## Contracts

- OpenAPI: `services/audit-log/contracts/openapi.yaml`

## Run locally

```bash
python -m tools.component_runner run --type service --name audit-log
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `AUDIT_LOG_STORAGE_PATH` | `services/audit-log/storage/audit-events.jsonl` | JSONL storage file for audit events |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `PORT` | `8080` | HTTP port for the service |

## Example request

```bash
curl -X POST http://localhost:8080/audit/events \
  -H "Content-Type: application/json" \
  -d '{
    "id": "evt-001",
    "timestamp": "2025-01-01T00:00:00Z",
    "actor": {"id": "user-1", "type": "user"},
    "action": "portfolio.create",
    "resource": {"id": "port-9", "type": "portfolio"},
    "outcome": "success"
  }'
```

## Tests

```bash
pytest services/audit-log/tests
```
