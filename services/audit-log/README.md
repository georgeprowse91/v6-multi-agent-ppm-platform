# Audit Log Service

The audit log service captures and stores audit events for compliance, traceability, and security
reviews across the platform. It validates incoming events against the canonical audit-event schema
and persists them to an encrypted, append-only WORM store (Azure Blob or local encrypted storage).

## Contracts

- OpenAPI: `services/audit-log/contracts/openapi.yaml`

## Run locally

```bash
python -m tools.component_runner run --type service --name audit-log
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `AUDIT_WORM_CONNECTION_STRING` | unset | Azure Blob connection string for WORM storage |
| `AUDIT_WORM_CONTAINER` | `audit-events` | Azure Blob container name |
| `AUDIT_WORM_LOCAL_PATH` | `services/audit-log/storage/immutable` | Local encrypted WORM path |
| `AUDIT_LOG_ENCRYPTION_KEY` | generated | Base64 Fernet key for local encryption |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `PORT` | `8080` | HTTP port for the service |

In AKS, supply `AUDIT_WORM_CONNECTION_STRING` and `AUDIT_LOG_ENCRYPTION_KEY` via Azure Key Vault and the
Secrets Store CSI driver rather than plaintext environment variables.

## Example request

```bash
curl -X POST http://localhost:8080/audit/events \
  -H "Content-Type: application/json" \
  -d '{
    "id": "evt-001",
    "timestamp": "2025-01-01T00:00:00Z",
    "tenant_id": "tenant-alpha",
    "actor": {"id": "user-1", "type": "user", "roles": ["auditor"]},
    "action": "portfolio.create",
    "resource": {"id": "port-9", "type": "portfolio"},
    "outcome": "success",
    "classification": "internal"
  }'
```

## Tests

```bash
pytest services/audit-log/tests
```
