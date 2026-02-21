from __future__ import annotations

import logging
import os
from typing import Any, cast

from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger("observability.logging")

_CONFIGURED = False


def configure_logging(service_name: str) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT", "http://otel-collector:4318/v1/logs")
    resource = Resource.create({"service.name": service_name})
    provider = LoggerProvider(resource=resource)
    processor = BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint))
    provider_obj = cast(Any, provider)
    add_processor = getattr(provider_obj, "add_log_record_processor", None)
    if callable(add_processor):
        add_processor(processor)
    set_logger_provider(provider)

    handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
    if hasattr(handler, "level"):
        logging.getLogger().addHandler(cast(logging.Handler, handler))

    _CONFIGURED = True
    logger.info("otel_logging_configured", extra={"service": service_name, "endpoint": endpoint})


__all__ = ["configure_logging"]
