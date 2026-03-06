# Operational Monitoring Dashboards

Reference guide for the PPM platform monitoring dashboards.

## SLO Dashboard

The SLO dashboard tracks key service level objectives:

- **API Availability**: Target 99.9% uptime measured via health endpoint checks.
- **Request Latency (p99)**: Target < 500ms for API gateway endpoints.
- **Error Rate**: Target < 0.1% of total requests.
- **Agent Response Time**: Target < 5s for single-agent queries.

### Accessing the Dashboard

1. Open the observability portal at the configured Grafana URL.
2. Navigate to the "PPM Platform SLOs" dashboard.
3. Select the environment (dev/staging/production) from the dropdown.

## Service Health Dashboard

Monitors the health of all 16 microservices:

- Pod readiness and liveness status
- Resource utilization (CPU, memory)
- Restart counts and crash loops
- Horizontal pod autoscaler status

## Agent Performance Dashboard

Tracks agent-specific metrics:

- Executions per agent per hour
- Average processing duration
- Success/failure ratios
- LLM token consumption

## Connector Sync Dashboard

Monitors connector synchronization:

- Sync job success/failure rates
- Data volume transferred
- Latency per connector
- Retry queue depth

## Alerting

Alerts are configured for:

- SLO burn rate exceeding budget
- Service health degradation
- Connector sync failures exceeding threshold
- Security events (auth failures, rate limit breaches)
