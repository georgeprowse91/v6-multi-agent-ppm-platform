# Audit Log Service

Captures and stores audit events for compliance and traceability.

## Current state

- Helm chart is available under `services/audit-log/helm/`.
- Storage backends are described under `services/audit-log/storage/`.
- No standalone API implementation yet.

## Quickstart

Validate the Helm chart:

```bash
python scripts/validate-helm-charts.py services/audit-log/helm
```

## How to verify

```bash
ls services/audit-log/storage
```

Expected output lists storage configuration assets.

## Key files

- `services/audit-log/helm/`: deployment manifests.
- `services/audit-log/storage/`: storage layout notes.
- `services/audit-log/src/`: code scaffolding for the service.

## Example

Search for the audit log service name in the Helm chart:

```bash
rg -n "audit" services/audit-log/helm
```

## Next steps

- Implement ingestion APIs under `services/audit-log/src/`.
- Add retention configuration in `services/audit-log/storage/`.
