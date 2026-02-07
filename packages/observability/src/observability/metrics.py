from __future__ import annotations

import logging
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("observability.metrics")

_CONFIGURED = False
_METER: Any | None = None


@dataclass(frozen=True)
class KPIHandles:
    requests: Any
    errors: Any


@dataclass(frozen=True)
class MCPClientMetrics:
    requests: Any
    latency: Any


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, service_name: str) -> None:
        super().__init__(app)
        meter = configure_metrics(service_name)
        self._requests: Any = meter.create_counter(
            name="http_requests_total",
            description="HTTP requests processed",
            unit="1",
        )
        self._latency: Any = meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s",
        )
        self._service_name: str = service_name

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        attributes = {
            "service": self._service_name,
            "method": request.method,
            "status": response.status_code,
            "path": request.url.path,
        }
        self._requests.add(1, attributes)
        self._latency.record(elapsed, attributes)
        return response


def configure_metrics(service_name: str) -> Any:
    global _CONFIGURED, _METER
    if _CONFIGURED:
        if _METER is None:
            raise RuntimeError("Metrics meter is not configured")
        return _METER

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
    if not endpoint:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318/v1/metrics")

    resource = Resource.create({"service.name": service_name})
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint), export_interval_millis=10000
    )
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    _METER = metrics.get_meter(service_name)
    _CONFIGURED = True
    logger.info("otel_metrics_configured", extra={"service": service_name, "endpoint": endpoint})
    return _METER


def build_kpi_handles(service_name: str) -> KPIHandles:
    meter = configure_metrics(service_name)
    requests = meter.create_counter(
        name="business_requests_total",
        description="Total business operations handled",
        unit="1",
    )
    errors = meter.create_counter(
        name="business_errors_total",
        description="Total business operation errors",
        unit="1",
    )
    return KPIHandles(requests=requests, errors=errors)


def build_mcp_client_metrics(service_name: str) -> MCPClientMetrics:
    meter = configure_metrics(service_name)
    requests = meter.create_counter(
        name="mcp_client_requests_total",
        description="Total MCP client requests",
        unit="1",
    )
    latency = meter.create_histogram(
        name="mcp_client_latency_seconds",
        description="Latency of MCP client requests in seconds",
        unit="s",
    )
    return MCPClientMetrics(requests=requests, latency=latency)


agent_request_count = Counter(
    "agent_requests_total",
    "Total number of agent invocations",
    ["agent_name", "outcome"],
)

agent_request_latency = Histogram(
    "agent_request_latency_seconds",
    "Latency of agent invocations",
    ["agent_name"],
)


__all__ = [
    "configure_metrics",
    "build_kpi_handles",
    "build_mcp_client_metrics",
    "KPIHandles",
    "MCPClientMetrics",
    "RequestMetricsMiddleware",
    "agent_request_count",
    "agent_request_latency",
]
