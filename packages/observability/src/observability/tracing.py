from __future__ import annotations

import logging
import os
from typing import cast

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


def inject_trace_headers(headers: dict[str, str]) -> dict[str, str]:
    carrier = dict(headers)
    propagate.inject(carrier)
    return carrier


class TraceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str) -> None:
        super().__init__(app)
        self._service_name = service_name

    async def dispatch(self, request: Request, call_next) -> Response:
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
            response = cast(Response, await call_next(request))
            span.set_attribute("http.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR))
            return response


__all__ = ["configure_tracing", "TraceMiddleware", "inject_trace_headers"]
