# Observability Architecture

## Purpose

Define how the platform collects logs, metrics, and traces, and document the production telemetry stack, dashboards, and alerting used to meet SLOs/SLIs.

## Architecture-level context

Observability spans the API gateway, orchestration runtime, and connector layer. Telemetry feeds the System Health agent (Agent 25) and the Continuous Improvement agent (Agent 20) so they can detect degradations and drive improvements.

## Telemetry standards

- **Logs**: structured logs exported via OpenTelemetry and correlated with trace context.
- **Metrics**: request latency, error rates, throughput, connector sync duration/success, per-agent execution duration, retries, and execution cost.
- **Traces**: end-to-end spans across request routing, orchestration, and connector sync operations.

### Log schema (example)

```json
{
  "timestamp": "2026-01-15T14:30:00Z",
  "service": "agent-orchestrator",
  "trace_id": "trace-123",
  "level": "INFO",
  "message": "Plan executed",
  "context": {"intent": "create_project"}
}
```

### Correlation IDs and cost telemetry

- Every top-level user request receives a `correlation_id` (UUID) and propagates it through orchestrator context and downstream agent calls.
- Structured logs, audit events, and metrics include `correlation_id` so one query can be traced end-to-end across all participating agents.
- Agent metrics include:
  - `agent_execution_duration_seconds` histogram tagged with `agent_id`, `task_id`, and `correlation_id`.
  - `agent_retries_total` counter tagged by the same dimensions.
  - `agent_errors_total` counter tagged by the same dimensions.
  - Cost counters (`external_api_cost`, `llm_tokens_consumed`) tagged with `correlation_id` for request-level attribution.

## SLO/SLI targets

| SLI | Target | Notes |
| --- | --- | --- |
| API availability | 99.9% monthly | Measured at API gateway |
| p95 orchestration response time | < 2.0s | Excludes long-running syncs |
| Connector sync success | 99% | Per connector, per day |
| Error budget | 0.1% | Tied to availability |

## Implemented telemetry stack

### Instrumentation

- **API gateway** and **orchestration service** initialize OpenTelemetry tracing, metrics, and logging at startup.
- **Connectors** initialize OpenTelemetry via the connector SDK runtime to emit sync spans, duration metrics, record counts, and error counters.

### Collection + Export

OpenTelemetry Collector receives OTLP data and exports:

- **Metrics** → Prometheus (scrape the collector endpoint on `:8889`).
- **Traces** → Jaeger.
- **Logs** → Loki (Grafana log explorer), plus Azure Monitor for long-term retention.

Collector endpoints are configured via `JAEGER_COLLECTOR_ENDPOINT` and `LOKI_ENDPOINT` (see the telemetry service Helm values).

### Dashboards

Grafana dashboards are stored as JSON exports in `infra/observability/dashboards`:

- `ppm-platform.json` for latency, throughput, error rate, and connector sync duration.
- `ppm-slo.json` for SLO adherence, connector sync success, and error budget tracking.
- `multi_agent_tracing.json` for correlation-based multi-agent predictive views, retries/errors overlays, and cost breakdowns by agent.

#### Dashboard screenshots

![PPM platform dashboard](images/grafana-ppm-platform.svg)
![PPM SLO dashboard](images/grafana-ppm-slo.svg)

## Alerts

Alert rules aligned to SLOs/SLIs are defined in `infra/observability/alerts/ppm-alerts.yaml` and cover:

- API gateway latency/error-rate breaches.
- Workflow/orchestration failure rates.
- Connector sync error rate and high latency.

## Usage example

Locate observability runbooks:

```bash
ls docs/runbooks
```

## How to verify

Confirm this doc references SLOs:

```bash
rg -n "SLO" docs/architecture/observability-architecture.md
```

Expected output: table rows listing SLO targets.

## Related docs

- [Resilience Architecture](resilience-architecture.md)
- [Performance Architecture](performance-architecture.md)
- [System Health Agent](../agents/agent-catalog.md)
