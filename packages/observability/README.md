# Observability Package

Shared observability helpers intended for logs, metrics, and tracing.

## Current state

- Tracing and metrics helpers live in `packages/observability/src/observability`.
- Observability architecture is documented in `docs/architecture/observability-architecture.md`.

## Quickstart

Review the observability architecture:

```bash
sed -n '1,40p' docs/architecture/observability-architecture.md
```

## How to verify

```bash
rg -n "TraceMiddleware|RequestMetricsMiddleware" services apps
```

Expected output shows service wiring for distributed tracing + metrics.

## Key files

- `docs/architecture/observability-architecture.md`: design reference.
- `packages/observability/src/observability/tracing.py`: trace propagation and middleware.
- `packages/observability/src/observability/metrics.py`: metric exporter + HTTP/KPI helpers.

## Example

Search for pipeline names:

```bash
rg -n "configure_tracing" services apps
```

## Next steps

- Implement shared logging helpers in `packages/observability/src/`.
- Expand metric coverage as SLOs mature.
