# SLO/SLI Definitions

## Purpose

Define service-level objectives (SLOs) and the service-level indicators (SLIs) used to monitor the platform.

## Scope

- API Gateway (`apps/api-gateway`)
- Orchestration Service (`apps/orchestration-service`)
- Workflow Engine (`apps/workflow-engine`)
- Data Sync Service (`services/data-sync-service`)
- Audit Log Service (`services/audit-log`)

## Core SLIs

| SLI | Definition | Source |
| --- | --- | --- |
| Availability | Successful responses / total requests | HTTP request metrics via `packages/observability` |
| Latency (P95) | 95th percentile response time for critical endpoints | Metrics middleware in each service |
| Error rate | 5xx responses / total responses | HTTP request metrics |
| Queue freshness | Age of queued sync jobs | Data Sync Service status store |
| Workflow completion | Completed runs / total runs | Workflow engine status store |

## Suggested SLO targets

These targets are aligned with the SLO template in `docs/templates/quality/slo-alert-definition-cross.yaml` and should be adjusted per deployment.

- **Availability:** 99.9% over 30 days for API Gateway and Workflow Engine.
- **Latency (P95):** < 750 ms for `/v1/query` and `/v1/workflows/start` over 7 days.
- **Error rate:** < 0.5% 5xx responses for core APIs.
- **Queue freshness:** 95% of sync jobs start within 5 minutes of enqueue.

## Instrumentation sources

- **HTTP metrics:** `packages/observability` middleware emits request counters and latency histograms.
- **Workflow metrics:** Workflow engine exposes status state; use scheduled checks to compute completion ratios.
- **Audit metrics:** Audit log emits ingestion counters and error counts.

## Operational guidance

1. Create an SLO definition per service using `docs/templates/quality/slo-alert-definition-cross.yaml`.
2. Store the finalized SLO spec in your deployment repository or monitoring system.
3. Link each SLO to the relevant runbooks (incident response, data sync failures, LLM degradation).

## Verification steps

- Inspect the SLO template:
  ```bash
  sed -n '1,160p' docs/templates/quality/slo-alert-definition-cross.yaml
  ```
- Confirm metrics middleware is registered:
  ```bash
  rg -n "RequestMetricsMiddleware" apps services | head -n 20
  ```

## Implementation status

- **Implemented:** Metrics middleware in services and apps.
- **Implemented:** Grafana dashboards and error budget alerts in `ops/infra/observability/dashboards` and `ops/infra/observability/alerts`.

## Related docs

- [Observability Architecture](../architecture/observability-architecture.md)
- [Runbook: Incident Response](incident-response.md)
- [Runbook: LLM Degradation](llm-degradation.md)
