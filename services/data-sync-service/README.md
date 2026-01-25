# Data Sync Service

Background synchronization and reconciliation for connector data.

## Current state

- Helm chart lives at `services/data-sync-service/helm/`.
- Synchronization rules are under `services/data-sync-service/rules/`.
- No runtime worker process is wired yet.

## Quickstart

Validate the Helm chart:

```bash
python scripts/validate-helm-charts.py services/data-sync-service/helm
```

## How to verify

```bash
ls services/data-sync-service/rules
```

Expected output lists synchronization rule files.

## Key files

- `services/data-sync-service/helm/`: deployment assets.
- `services/data-sync-service/rules/`: reconciliation rules.
- `services/data-sync-service/src/`: implementation scaffolding.

## Example

Search for rule identifiers:

```bash
rg -n "rule" services/data-sync-service/rules
```

## Next steps

- Implement sync workers under `services/data-sync-service/src/`.
- Wire connector outputs from `apps/connector-hub/`.
