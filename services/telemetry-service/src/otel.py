from __future__ import annotations

import importlib.util
import os
from contextlib import nullcontext
from typing import Any

trace: Any
Resource: Any
TracerProvider: Any
BatchSpanProcessor: Any
OTLPSpanExporter: Any
configure_azure_monitor: Any

_HAS_OTEL = importlib.util.find_spec("opentelemetry") is not None
_HAS_OTEL_EXPORTER = importlib.util.find_spec("opentelemetry.exporter") is not None
_HAS_AZURE_MONITOR = importlib.util.find_spec("azure.monitor.opentelemetry") is not None

if _HAS_OTEL:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
else:
    trace = None
    Resource = None
    TracerProvider = None
    BatchSpanProcessor = None

if _HAS_OTEL_EXPORTER:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter as _OTLPSpanExporter,
    )

    OTLPSpanExporter = _OTLPSpanExporter
else:
    OTLPSpanExporter = None

if _HAS_AZURE_MONITOR:
    from azure.monitor.opentelemetry import (
        configure_azure_monitor as _configure_azure_monitor,
    )

    configure_azure_monitor = _configure_azure_monitor
else:
    configure_azure_monitor = None


class _NoopTracer:
    def start_as_current_span(self, _name: str):
        return nullcontext()


class _NoopTrace:
    def set_tracer_provider(self, _provider) -> None:
        return None

    def get_tracer(self, _name: str) -> _NoopTracer:
        return _NoopTracer()


class TelemetryPipeline:
    def __init__(self) -> None:
        self._configured = False

    def configure(self) -> None:
        if self._configured:
            return
        if (
            trace is None
            or TracerProvider is None
            or Resource is None
            or BatchSpanProcessor is None
        ):
            self._configured = True
            return
        connection_string = os.getenv("AZURE_MONITOR_CONNECTION_STRING")
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

        resource = Resource.create({"service.name": "telemetry-service"})
        provider = TracerProvider(resource=resource)
        if otlp_endpoint and OTLPSpanExporter is not None:
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        if connection_string and configure_azure_monitor is not None:
            configure_azure_monitor(connection_string=connection_string)

        self._configured = True

    def tracer(self):
        if trace is None:
            return _NoopTracer()
        self.configure()
        return trace.get_tracer("telemetry-service")


PIPELINE = TelemetryPipeline()
