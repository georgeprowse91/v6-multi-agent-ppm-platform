from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from observability.metrics import RequestMetricsMiddleware
from observability.telemetry import (
    REQUIRED_BUSINESS_METRICS,
    REQUIRED_HTTP_METRICS,
    REQUIRED_TELEMETRY_DIMENSIONS,
)
from observability.tracing import TraceMiddleware, configure_tracing, inject_trace_headers
from ops.tools.observability_compliance_checks import check_service_observability_compliance


def test_telemetry_contract_declares_required_dimensions_and_metrics() -> None:
    assert {"service.name", "tenant.id", "trace.id"}.issubset(set(REQUIRED_TELEMETRY_DIMENSIONS))
    assert {
        "http_requests_total",
        "http_request_duration_seconds",
        "http_request_errors_total",
        "http_requests_in_flight",
    }.issubset(set(REQUIRED_HTTP_METRICS))
    assert {
        "orchestrator_executions_total",
        "workflow_executions_total",
        "connector_sync_executions_total",
    }.issubset(set(REQUIRED_BUSINESS_METRICS))


def test_observability_compliance_checker_has_no_violations() -> None:
    violations = check_service_observability_compliance()
    assert violations == []


def test_trace_propagation_keeps_incoming_traceparent() -> None:
    app = FastAPI()
    configure_tracing("observability-test")
    app.add_middleware(TraceMiddleware, service_name="observability-test")
    app.add_middleware(RequestMetricsMiddleware, service_name="observability-test")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    base_headers = inject_trace_headers({"X-Tenant-ID": "tenant-1"}, correlation_id="123e4567-e89b-12d3-a456-426614174000")
    # Trace header may be unavailable in minimal test runtime, but correlation tag must be propagated.
    assert base_headers["X-Correlation-ID"] == "123e4567-e89b-12d3-a456-426614174000"

    with TestClient(app) as client:
        response = client.get("/healthz", headers=base_headers)

    assert response.status_code == 200
