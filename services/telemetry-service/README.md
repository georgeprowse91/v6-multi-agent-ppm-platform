# Telemetry Service

Central ingestion and processing for logs, metrics, and traces.

## Current state

- Helm chart under `services/telemetry-service/helm/`.
- Pipeline definitions under `services/telemetry-service/pipelines/`.
- Service implementation is not wired yet.

## Quickstart

Validate the Helm chart:

```bash
python scripts/validate-helm-charts.py services/telemetry-service/helm
```

## How to verify

```bash
ls services/telemetry-service/pipelines
```

Expected output includes telemetry pipeline definitions.

## Key files

- `services/telemetry-service/pipelines/`: telemetry pipeline configs.
- `services/telemetry-service/helm/`: deployment assets.
- `services/telemetry-service/src/`: service scaffolding.

## Example

Search for pipeline names:

```bash
rg -n "pipeline" services/telemetry-service/pipelines
```

## Next steps

- Implement ingestion workers under `services/telemetry-service/src/`.
- Wire outputs to analytics models in `apps/analytics-service/`.
