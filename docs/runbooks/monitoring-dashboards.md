# Operational Monitoring Dashboards

This runbook describes the dashboards used to monitor production health.

## Primary dashboards
- **SLO Dashboard:** `ops/infra/observability/dashboards/ppm-slo.json` for latency, error rate, and availability.
- **Alert overview:** `ops/infra/observability/alerts/ppm-alerts.yaml` defines alert rules tied to SLOs.
- **Tracing view:** OpenTelemetry traces for end-to-end workflow execution.
- **Connector health:** monitor sync lag, error rates, and job throughput.

## Usage guidelines
- Validate dashboards before release cutover.
- During incidents, capture dashboard snapshots for the postmortem.
- Ensure dashboard access is limited to on-call and operations roles.

## Dashboard validation checklist
- [ ] SLO panels show live metrics.
- [ ] Alert rules are enabled and routed to on-call.
- [ ] Trace sampling is configured for critical endpoints.
- [ ] Connector health dashboard shows job success rates.
