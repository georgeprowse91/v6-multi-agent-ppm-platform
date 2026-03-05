# System Health Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the System Health Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Monitor platform service health via configurable health probes and endpoint checks.
- Aggregate system telemetry from Azure Monitor, Application Insights, and Log Analytics.
- Track SLO/SLA compliance and compute system health scores.
- Detect anomalies in system metrics using Azure Anomaly Detector.
- Route alerts to PagerDuty, OpsGenie, and ServiceNow for incident management.
- Trigger auto-scaling actions when resource thresholds are breached.
- Publish system health events and metrics via Event Hub and Prometheus.

### Inputs
- `action`: `check_health`, `get_system_status`, `run_diagnostics`, `get_metrics`, `create_alert`, `acknowledge_alert`.
- Health probe definitions (endpoints, timeouts, intervals).
- Telemetry queries against Log Analytics and Application Insights.
- Alert and scaling threshold configurations.
- `context`: `tenant_id`, `correlation_id` (optional; used for audit/event metadata).

### Outputs
- Aggregated health status (per-service and composite scores).
- System metrics (CPU, memory, queue depth, latency, error rates).
- Alert records with severity, status, and routing information.
- Anomaly detection results with confidence scores.
- Scaling event records and automation outcomes.
- Event payloads published to Event Hub for downstream analytics.

### Decision responsibilities
- Determine overall system health status based on probe results and metric thresholds.
- Decide alert severity and routing (PagerDuty, OpsGenie, ServiceNow) based on configured rules.
- Trigger auto-scaling when CPU, memory, or queue depth thresholds are exceeded.
- Identify anomalous metric patterns and flag for investigation.

### Must / must-not behaviors
- **Must** validate health probe configurations before execution.
- **Must** publish health status and telemetry events to configured sinks (Event Hub, Prometheus).
- **Must** route high-priority alerts to configured webhook endpoints.
- **Must** record incident creation and updates in ServiceNow when configured.
- **Must not** modify application code or deployment configurations directly.
- **Must not** perform portfolio-level analytics or KPI computation (delegated to the Analytics Insights agent).
- **Must not** execute change management workflows (delegated to the Change Control agent).

## Overlap & handoff boundaries

### Analytics Insights
- **Overlap risk**: both agents handle metrics and telemetry data.
- **Boundary**: The System Health agent focuses on system-level health telemetry, alerts, and SLO monitoring. The Analytics Insights agent focuses on portfolio health analytics, narrative generation, and business KPI dashboarding. The Analytics Insights agent can consume system health signals as inputs to dashboards or narrative summaries.

### Change Control
- **Overlap risk**: system health incidents may trigger change requests.
- **Boundary**: The System Health agent detects and alerts on system health issues. The Change Control agent owns change request intake, classification, and approval workflows. The System Health agent may emit events that trigger change workflows but does not create or manage change records.

## Functional gaps / inconsistencies & alignment needs

- **Event taxonomy alignment**: ensure system health events use consistent naming with the platform-wide event schema.
- **Alert routing configuration**: document the precedence and fallback behavior when multiple alert webhook endpoints are configured.
- **Scaling action audit trail**: ensure auto-scaling actions are logged and published as events for governance and analytics consumption.
- **UI alignment**: system health dashboards should surface probe status, SLO compliance, and alert history.

## Checkpoint: system health monitoring + dependency map entry

### Health monitoring criteria
- All configured health probes return healthy status within timeout.
- SLO metrics (availability, latency, error rate) are within defined thresholds.
- Anomaly detection scores are below alert thresholds.
- Alert routing webhooks are reachable and configured.

### Dependency map entry
- **Upstream**: Azure Monitor, Application Insights, Log Analytics, health probe endpoints.
- **Core services**: Event Hub, Prometheus, PagerDuty/OpsGenie webhooks, ServiceNow API.
- **Downstream**: Analytics Insights agent (health telemetry for dashboards), Change Control agent (incident-triggered changes).

## What's inside

- [src](/agents/operations-management/system-health-agent/src): Implementation source for this component.
- [tests](/agents/operations-management/system-health-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/operations-management/system-health-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name system-health-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/system-health-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Monitoring setup

The system health agent initializes Azure Monitor, Application Insights, and Log Analytics clients when the following environment variables are provided:

- `MONITOR_WORKSPACE_ID`: Log Analytics workspace ID for querying historical metrics.
- `APPINSIGHTS_INSTRUMENTATION_KEY`: Application Insights key used to build the Azure Monitor connection string.
- `AZURE_MONITOR_CONNECTION_STRING`: (Optional) Overrides the connection string used by OpenTelemetry exporters.

It also supports OpenTelemetry exporters (Azure Monitor), Prometheus metrics, and Event Hub telemetry delivery:

- `PROMETHEUS_METRICS_PORT`: Port for the Prometheus `/metrics` endpoint (set to `0` to disable).
- `EVENT_HUB_CONNECTION_STRING`: Azure Event Hub connection string.
- `EVENT_HUB_NAME`: Event Hub name for telemetry events.
- `EVENT_HUB_PARTITIONS`: Partition count for high-volume events (documented for provisioning).
- `EVENT_HUB_THROUGHPUT_UNITS`: Throughput unit count for high-volume events.

Alert routing and automation are configured with webhook-style integrations:

- `PAGERDUTY_WEBHOOK_URL`, `OPSGENIE_WEBHOOK_URL`: High-priority alert webhooks.
- `SCALING_WEBHOOK_URL`: Logic App/Azure Automation webhook for scaling events.
- `SCALING_THRESHOLD_CPU`, `SCALING_THRESHOLD_MEMORY`, `SCALING_THRESHOLD_QUEUE_DEPTH`: Thresholds that trigger scaling.

ServiceNow integration (incident creation and updates) is enabled with:

- `SERVICENOW_INSTANCE_URL`, `SERVICENOW_USERNAME`, `SERVICENOW_PASSWORD` or `SERVICENOW_TOKEN`.

Anomaly detection can be enabled with Azure Anomaly Detector:

- `ANOMALY_DETECTOR_ENDPOINT`, `ANOMALY_DETECTOR_KEY`.

### Adding new health probes

Provide a JSON list of endpoints via `HEALTH_ENDPOINTS`. Example:

```json
[
  {"name": "api", "url": "https://api.example.com/health", "timeout_seconds": 5},
  {"name": "worker", "url": "https://worker.example.com/health", "timeout_seconds": 5}
]
```

Set `HEALTH_PROBE_INTERVAL_SECONDS` to control the probe cadence. The agent publishes aggregated health status via its API responses (for `check_health` and `get_system_status`) and emits the same payload to Event Hub when configured.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
