from __future__ import annotations

import logging
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

REPO_ROOT = Path(__file__).resolve().parents[4]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from observability.logging import configure_logging  # noqa: E402
from observability.metrics import configure_metrics  # noqa: E402
from observability.tracing import configure_tracing  # noqa: E402

logger = logging.getLogger("connector-telemetry")


@dataclass
class ConnectorTelemetry:
    connector_id: str
    service_name: str
    sync_duration: Any
    sync_records: Any
    sync_errors: Any
    sync_total: Any

    @contextmanager
    def track_sync(self, operation: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        start = time.perf_counter()
        span_attributes = {
            "connector_id": self.connector_id,
            "connector_operation": operation,
            "service_name": self.service_name,
        }
        if attributes:
            span_attributes.update(attributes)
        tracer = trace.get_tracer(self.service_name)
        with tracer.start_as_current_span(
            f"connector.sync.{operation}", kind=SpanKind.INTERNAL
        ) as span:
            for key, value in span_attributes.items():
                span.set_attribute(key, value)
            try:
                yield span_attributes
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                self.sync_errors.add(1, span_attributes)
                raise
            finally:
                duration = time.perf_counter() - start
                self.sync_duration.record(duration, span_attributes)
                self.sync_total.add(1, span_attributes)

    def record_records(self, count: int, attributes: dict[str, Any]) -> None:
        self.sync_records.add(count, attributes)


_TELEMETRY: dict[str, ConnectorTelemetry] = {}


class _NoopMetric:
    def add(self, *_args: object, **_kwargs: object) -> None:
        return None

    def record(self, *_args: object, **_kwargs: object) -> None:
        return None


def get_connector_telemetry(connector_id: str) -> ConnectorTelemetry:
    if connector_id in _TELEMETRY:
        return _TELEMETRY[connector_id]

    service_name = f"connector-{connector_id}"
    if os.getenv("CONNECTOR_TELEMETRY_DISABLED") == "1":
        telemetry = ConnectorTelemetry(
            connector_id=connector_id,
            service_name=service_name,
            sync_duration=_NoopMetric(),
            sync_records=_NoopMetric(),
            sync_errors=_NoopMetric(),
            sync_total=_NoopMetric(),
        )
        _TELEMETRY[connector_id] = telemetry
        return telemetry
    configure_tracing(service_name)
    configure_logging(service_name)

    meter = configure_metrics(service_name)
    sync_duration = meter.create_histogram(
        name="connector_sync_duration_seconds",
        description="Connector sync duration in seconds",
        unit="s",
    )
    sync_records = meter.create_counter(
        name="connector_sync_records_total",
        description="Total records produced by connector sync",
        unit="1",
    )
    sync_errors = meter.create_counter(
        name="connector_sync_errors_total",
        description="Total connector sync errors",
        unit="1",
    )
    sync_total = meter.create_counter(
        name="connector_sync_total",
        description="Total connector sync runs",
        unit="1",
    )

    telemetry = ConnectorTelemetry(
        connector_id=connector_id,
        service_name=service_name,
        sync_duration=sync_duration,
        sync_records=sync_records,
        sync_errors=sync_errors,
        sync_total=sync_total,
    )
    _TELEMETRY[connector_id] = telemetry
    logger.info("connector_telemetry_configured", extra={"connector_id": connector_id})
    return telemetry


__all__ = ["ConnectorTelemetry", "get_connector_telemetry"]
