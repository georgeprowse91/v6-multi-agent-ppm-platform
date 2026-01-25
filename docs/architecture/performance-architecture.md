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

## Implementation status

- **Planned**: performance test harness and load testing.
- **Implemented**: documented targets and runbook references.

## Related docs

- [Observability Architecture](observability-architecture.md)
- [Resilience Architecture](resilience-architecture.md)
- [Runbooks](../runbooks/)
