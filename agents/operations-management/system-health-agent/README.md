# System Health Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the System Health Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

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
