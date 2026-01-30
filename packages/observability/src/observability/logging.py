from __future__ import annotations

import logging
import os

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
    provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint)))
    set_logger_provider(provider)

    handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
    logging.getLogger().addHandler(handler)

    _CONFIGURED = True
    logger.info("otel_logging_configured", extra={"service": service_name, "endpoint": endpoint})


__all__ = ["configure_logging"]
