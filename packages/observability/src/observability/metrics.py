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

try:
    from prometheus_client import Counter, Histogram
except ModuleNotFoundError:  # pragma: no cover - optional dependency

    class _NoopPromMetric:
        def labels(self, *_args: object, **_kwargs: object) -> _NoopPromMetric:
            return self

        def inc(self, *_args: object, **_kwargs: object) -> None:
            return None

        def observe(self, *_args: object, **_kwargs: object) -> None:
            return None

    def Counter(*_args: object, **_kwargs: object) -> _NoopPromMetric:  # noqa: N802
        return _NoopPromMetric()

    def Histogram(*_args: object, **_kwargs: object) -> _NoopPromMetric:  # noqa: N802
        return _NoopPromMetric()


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from observability.telemetry import REQUIRED_BUSINESS_METRICS, REQUIRED_HTTP_METRICS
from observability.tracing import get_trace_id

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


@dataclass(frozen=True)
class MCPFallbackMetrics:
    fallbacks: Any


@dataclass(frozen=True)
class CostMetrics:
    llm_tokens_consumed: Any
    external_api_cost: Any


@dataclass(frozen=True)
class AgentExecutionMetrics:
    duration_seconds: Any
    retries_total: Any
    errors_total: Any


@dataclass(frozen=True)
class WorkflowBusinessMetrics:
    executions_total: Any
    execution_duration_seconds: Any


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
        self._errors: Any = meter.create_counter(
            name="http_request_errors_total",
            description="HTTP request failures for error-rate tracking",
            unit="1",
        )
        create_up_down_counter = getattr(meter, "create_up_down_counter", None)
        if callable(create_up_down_counter):
            self._in_flight: Any = create_up_down_counter(
                name="http_requests_in_flight",
                description="In-flight HTTP requests for saturation tracking",
                unit="1",
            )
        else:
            self._in_flight = meter.create_counter(
                name="http_requests_in_flight",
                description="Fallback in-flight request counter when up/down counters are unavailable",
                unit="1",
            )
        self._service_name: str = service_name

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        tenant_id = request.headers.get("X-Tenant-ID", "unknown")
        self._in_flight.add(1, {"service.name": self._service_name, "tenant.id": tenant_id})
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        attributes = {
            "service.name": self._service_name,
            "tenant.id": tenant_id,
            "trace.id": get_trace_id() or "unavailable",
            "method": request.method,
            "status": response.status_code,
            "path": request.url.path,
        }
        self._requests.add(1, attributes)
        self._latency.record(elapsed, attributes)
        if response.status_code >= 500:
            self._errors.add(1, attributes)
        self._in_flight.add(-1, {"service.name": self._service_name, "tenant.id": tenant_id})
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


def build_mcp_fallback_metrics(service_name: str) -> MCPFallbackMetrics:
    meter = configure_metrics(service_name)
    fallbacks = meter.create_counter(
        name="mcp_client_fallback_total",
        description="Total MCP client fallbacks to REST",
        unit="1",
    )
    return MCPFallbackMetrics(fallbacks=fallbacks)


def build_cost_metrics(service_name: str) -> CostMetrics:
    meter = configure_metrics(service_name)
    llm_tokens_consumed = meter.create_counter(
        name="llm_tokens_consumed",
        description="Total LLM tokens consumed by prompt/completion usage",
        unit="1",
    )
    external_api_cost = meter.create_counter(
        name="external_api_cost",
        description="Total estimated cost of external connector/API calls",
        unit="AUD",
    )
    return CostMetrics(
        llm_tokens_consumed=llm_tokens_consumed,
        external_api_cost=external_api_cost,
    )


def build_agent_execution_metrics(service_name: str) -> AgentExecutionMetrics:
    meter = configure_metrics(service_name)
    duration_seconds = meter.create_histogram(
        name="agent_execution_duration_seconds",
        description="Execution duration for agent runs",
        unit="s",
    )
    retries_total = meter.create_counter(
        name="agent_retries_total",
        description="Total retries per agent execution",
        unit="1",
    )
    errors_total = meter.create_counter(
        name="agent_errors_total",
        description="Total agent execution errors",
        unit="1",
    )
    return AgentExecutionMetrics(
        duration_seconds=duration_seconds,
        retries_total=retries_total,
        errors_total=errors_total,
    )


def build_business_workflow_metrics(service_name: str, workflow: str) -> WorkflowBusinessMetrics:
    meter = configure_metrics(service_name)
    executions_total = meter.create_counter(
        name=f"{workflow}_executions_total",
        description=f"Total execution count for {workflow}",
        unit="1",
    )
    execution_duration_seconds = meter.create_histogram(
        name=f"{workflow}_execution_duration_seconds",
        description=f"Execution duration for {workflow}",
        unit="s",
    )
    return WorkflowBusinessMetrics(
        executions_total=executions_total,
        execution_duration_seconds=execution_duration_seconds,
    )


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
    "build_mcp_fallback_metrics",
    "build_cost_metrics",
    "build_agent_execution_metrics",
    "build_business_workflow_metrics",
    "KPIHandles",
    "MCPClientMetrics",
    "MCPFallbackMetrics",
    "CostMetrics",
    "AgentExecutionMetrics",
    "RequestMetricsMiddleware",
    "WorkflowBusinessMetrics",
    "agent_request_count",
    "agent_request_latency",
    "REQUIRED_HTTP_METRICS",
    "REQUIRED_BUSINESS_METRICS",
]
