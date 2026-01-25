# Observability Architecture

## Purpose

Define how the platform collects logs, metrics, and traces, and establish initial SLO/SLI targets for production readiness.

## Architecture-level context

Observability spans the API gateway, agent runtime, and connector layer. Telemetry is used by the System Health agent (Agent 25) and the Continuous Improvement agent (Agent 20) to detect degradations and feed improvements.

## Telemetry standards

- **Logs**: structured JSON with correlation IDs.
- **Metrics**: request latency, error rates, queue depth, connector sync success.
- **Traces**: end-to-end spans across intent routing, agent calls, and connector sync.

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

## Initial SLO/SLI targets (planned)

| SLI | Target | Notes |
| --- | --- | --- |
| API availability | 99.9% monthly | Measured at API gateway |
| p95 agent response time | < 2.0s | Excludes long-running syncs |
| Connector sync success | 99% | Per connector, per day |
| Error budget | 0.1% | Tied to availability |

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

## Implementation status

- **Planned**: production telemetry pipelines and dashboards.
- **Implemented**: documentation and runbook references.

## Related docs

- [Resilience Architecture](resilience-architecture.md)
- [Performance Architecture](performance-architecture.md)
- [System Health Agent](../agents/agent-catalog.md)
