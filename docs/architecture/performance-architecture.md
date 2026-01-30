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

The performance test harness lives under `tests/performance/` and uses Locust to drive concurrent API and connector traffic based on a YAML configuration. The harness supports configurable user counts, spawn rates, request pacing, and test duration, plus CSV exports for latency, throughput, and error rates. Locust results are summarized in CI for pull requests so reviewers can see baseline metrics before merging.

## Test results

CI runs the harness against a lightweight mock API server to validate the load workflow and to capture baseline stats. The workflow publishes a markdown summary that includes total requests, failures, requests per second, average latency, and p95 latency for each configured endpoint. Teams should update `tests/performance/config.yaml` to target staging or production-like environments when running deeper performance validations.

## Implementation status

- **Implemented**: performance test harness, CI summary reporting, documented targets, and runbook references.

## Related docs

- [Observability Architecture](observability-architecture.md)
- [Resilience Architecture](resilience-architecture.md)
- [Runbooks](../runbooks/)
