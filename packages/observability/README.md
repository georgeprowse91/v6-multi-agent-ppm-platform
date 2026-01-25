# Observability Package

Shared observability helpers intended for logs, metrics, and tracing.

## Current state

- No package implementation is present yet in `packages/observability/`.
- Observability architecture is documented in `docs/architecture/observability-architecture.md`.

## Quickstart

Review the observability architecture:

```bash
sed -n '1,40p' docs/architecture/observability-architecture.md
```

## How to verify

```bash
ls services/telemetry-service/pipelines
```

Expected output lists telemetry pipeline configs.

## Key files

- `docs/architecture/observability-architecture.md`: design reference.
- `services/telemetry-service/pipelines/`: pipeline definitions.

## Example

Search for pipeline names:

```bash
rg -n "pipeline" services/telemetry-service/pipelines
```

## Next steps

- Implement shared logging helpers in `packages/observability/src/`.
- Wire the helpers into `services/telemetry-service/`.
