from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, cast

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("observability.metrics")

_CONFIGURED = False
_METER = None


@dataclass(frozen=True)
class KPIHandles:
    requests: Any
    errors: Any


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str) -> None:
        super().__init__(app)
        meter = configure_metrics(service_name)
        self._requests = meter.create_counter(
            name="http_requests_total",
            description="HTTP requests processed",
            unit="1",
        )
        self._latency = meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s",
        )
        self._service_name = service_name

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = cast(Response, await call_next(request))
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


def configure_metrics(service_name: str):
    global _CONFIGURED, _METER
    if _CONFIGURED:
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


__all__ = [
    "configure_metrics",
    "build_kpi_handles",
    "KPIHandles",
    "RequestMetricsMiddleware",
]
