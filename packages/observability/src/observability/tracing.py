from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("observability.tracing")

_CONFIGURED = False
_PROPAGATOR = TraceContextTextMapPropagator()


def configure_tracing(service_name: str) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318/v1/traces")
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    propagate.set_global_textmap(_PROPAGATOR)
    _CONFIGURED = True
    logger.info("otel_tracing_configured", extra={"service": service_name, "endpoint": endpoint})


def _correlation_to_trace_hex(correlation_id: str | None) -> str | None:
    if not correlation_id:
        return None
    try:
        return UUID(str(correlation_id)).hex
    except (ValueError, AttributeError, TypeError):
        normalized = str(correlation_id).replace("-", "").strip().lower()
        if len(normalized) == 32 and all(ch in "0123456789abcdef" for ch in normalized):
            return normalized
        return None


def _context_with_correlation_trace(correlation_id: str | None) -> Any | None:
    trace_hex = _correlation_to_trace_hex(correlation_id)
    if not trace_hex:
        return None
    trace_id = int(trace_hex, 16)
    span_context_type = getattr(trace, "SpanContext", None)
    non_recording_span_type = getattr(trace, "NonRecordingSpan", None)
    trace_flags_type = getattr(trace, "TraceFlags", None)
    trace_state_type = getattr(trace, "TraceState", None)
    set_span_in_context = getattr(trace, "set_span_in_context", None)
    if not all([span_context_type, non_recording_span_type, trace_flags_type, trace_state_type, set_span_in_context]):
        return None
    parent_span_context = span_context_type(
        trace_id=trace_id,
        span_id=1,
        is_remote=True,
        trace_flags=trace_flags_type(0x01),
        trace_state=trace_state_type(),
    )
    parent_span = non_recording_span_type(parent_span_context)
    return set_span_in_context(parent_span)


def inject_trace_headers(headers: dict[str, str], correlation_id: str | None = None) -> dict[str, str]:
    carrier = dict(headers)
    if correlation_id:
        carrier["X-Correlation-ID"] = correlation_id
    context = _context_with_correlation_trace(correlation_id)
    if context is not None:
        propagate.inject(carrier, context=context)
    else:
        propagate.inject(carrier)
    return carrier


def get_trace_id() -> str | None:
    span = trace.get_current_span()
    if not span:
        return None
    trace_id = span.get_span_context().trace_id
    if not trace_id:
        return None
    return f"{trace_id:032x}"


@contextmanager
def start_agent_span(
    agent_name: str,
    attributes: dict[str, str] | None = None,
    correlation_id: str | None = None,
) -> Iterator[Any]:
    tracer = trace.get_tracer(agent_name)
    span_context = _context_with_correlation_trace(correlation_id)
    span_kwargs: dict[str, Any] = {"kind": SpanKind.INTERNAL}
    if span_context is not None:
        span_kwargs["context"] = span_context
    with tracer.start_as_current_span(f"agent.execute.{agent_name}", **span_kwargs) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        if correlation_id:
            span.set_attribute("correlation.id", correlation_id)
        yield span


class TraceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, service_name: str) -> None:
        super().__init__(app)
        self._service_name: str = service_name

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        tracer = trace.get_tracer(self._service_name)
        context = propagate.extract(dict(request.headers))
        span_name = f"{request.method} {request.url.path}"
        with tracer.start_as_current_span(span_name, context=context, kind=SpanKind.SERVER) as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.target", request.url.path)
            span.set_attribute("http.scheme", request.url.scheme)
            span.set_attribute("http.client_ip", request.client.host if request.client else "")
            span.set_attribute("http.user_agent", request.headers.get("user-agent", ""))
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR))
            return response


__all__ = [
    "configure_tracing",
    "TraceMiddleware",
    "inject_trace_headers",
    "get_trace_id",
    "start_agent_span",
]
