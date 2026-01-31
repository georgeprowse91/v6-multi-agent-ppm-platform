# Performance Architecture

## Purpose

Define performance targets, caching strategies, and workload assumptions for the platform.

## Architecture-level context

Performance tuning spans the API gateway, agent orchestration, connector sync schedules, and data storage. Performance targets inform infrastructure sizing in `infra/` and SLOs in `docs/runbooks/slo-sli.md`.

## Performance targets (initial)

| Area | Target |
| --- | --- |
| API p95 latency | < 2.0s |
| Agent plan creation | < 1.0s |
| Connector sync window | < 30 min per connector |
| Batch ingestion | 5k work items/min |

## Optimization strategies

- **Caching**: use Redis for frequently accessed portfolios and user profiles.
- **Async orchestration**: long-running tasks delegated to workflows.
- **Connector throttling**: obey vendor rate limits and stagger syncs.
- **Data partitioning**: partition project data by tenant and time.

## Usage example

Review SLO/SLI targets:

```bash
sed -n '1,160p' docs/runbooks/slo-sli.md
```

## How to verify

Check the performance targets table:

```bash
rg -n "API p95" docs/architecture/performance-architecture.md
```

Expected output: performance target entries.

## Performance test harness

The primary performance harness lives under `tests/load/` and executes SLA-driven load scenarios against staging or production deployments. Targets and thresholds are captured in `tests/load/sla_targets.json`, and the harness:

- Issues concurrent HTTP requests to the configured endpoints.
- Calculates average latency, p95 latency, error rate, and throughput.
- Fails CI when any SLA threshold is violated.

The harness defaults to the staging API gateway but supports overrides for alternate environments and auth headers via environment variables (see `tests/load/README.md`).

## Interpreting results

Each load scenario produces:

- **Average latency**: mean response time across the request set.
- **P95 latency**: tail latency for the slowest 5% of requests.
- **Error rate**: proportion of HTTP responses with status >= 400 or network failures.
- **Throughput**: requests per second achieved during the scenario.

Use the `LOAD_PROFILE` environment variable to select SLA thresholds for `ci`, `staging`, or `production`.

## Where to view latency and error metrics

Use the Grafana dashboards exported under `infra/observability/dashboards`:

- `ppm-platform.json` for latency, throughput, and error rates across services.
- `ppm-slo.json` for SLO compliance and error budget burn.

Logs and traces are available via Loki and Jaeger per the observability stack described in `docs/architecture/observability-architecture.md`.

## Implementation status

- **Implemented**: SLA-based load harness targeting staging/production, CI gating on SLA violations, documented targets, and observability dashboards.

## Related docs

- [Observability Architecture](observability-architecture.md)
- [Resilience Architecture](resilience-architecture.md)
- [Runbooks](../runbooks/)
