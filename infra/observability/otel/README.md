# OpenTelemetry Configuration

OpenTelemetry collector configuration and exporters for **observability**. Keep separate configs for
local development and production.

The Helm chart for `telemetry-service` ships a synchronized copy of this collector configuration
to mount in cluster deployments. Update `services/telemetry-service/helm/files/collector.yaml`
alongside changes here. 
