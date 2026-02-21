from __future__ import annotations

from dataclasses import dataclass

REQUIRED_TELEMETRY_DIMENSIONS: tuple[str, ...] = (
    "service.name",
    "tenant.id",
    "trace.id",
)

REQUIRED_HTTP_METRICS: tuple[str, ...] = (
    "http_requests_total",
    "http_request_duration_seconds",
    "http_request_errors_total",
    "http_requests_in_flight",
)

REQUIRED_BUSINESS_METRICS: tuple[str, ...] = (
    "workflow_executions_total",
    "workflow_execution_duration_seconds",
    "connector_sync_executions_total",
    "connector_sync_execution_duration_seconds",
    "orchestrator_executions_total",
    "orchestrator_execution_duration_seconds",
)


@dataclass(frozen=True)
class TelemetryContract:
    required_dimensions: tuple[str, ...] = REQUIRED_TELEMETRY_DIMENSIONS
    required_http_metrics: tuple[str, ...] = REQUIRED_HTTP_METRICS
    required_business_metrics: tuple[str, ...] = REQUIRED_BUSINESS_METRICS


TELEMETRY_CONTRACT = TelemetryContract()


__all__ = [
    "REQUIRED_TELEMETRY_DIMENSIONS",
    "REQUIRED_HTTP_METRICS",
    "REQUIRED_BUSINESS_METRICS",
    "TelemetryContract",
    "TELEMETRY_CONTRACT",
]
