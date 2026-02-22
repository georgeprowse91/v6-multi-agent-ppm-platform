from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from fastapi.testclient import TestClient


def _install_opentelemetry_mocks() -> None:
    import sys

    if "opentelemetry" in sys.modules:
        return

    class _NoopMetric:
        def add(self, *args, **kwargs) -> None:
            return None

        def record(self, *args, **kwargs) -> None:
            return None

    class _Meter:
        def create_counter(self, *args, **kwargs):
            return _NoopMetric()

        def create_histogram(self, *args, **kwargs):
            return _NoopMetric()

    metrics_module = ModuleType("opentelemetry.metrics")
    metrics_module.set_meter_provider = lambda *args, **kwargs: None
    metrics_module.get_meter = lambda *args, **kwargs: _Meter()

    otel_module = ModuleType("opentelemetry")
    otel_module.metrics = metrics_module

    class _SpanContext:
        trace_id = 0

    class _Span:
        def set_attribute(self, *args, **kwargs) -> None:
            return None

        def set_status(self, *args, **kwargs) -> None:
            return None

        def get_span_context(self):
            return _SpanContext()

    class _SpanContextManager:
        def __init__(self):
            self._span = _Span()

        def __enter__(self):
            return self._span

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    class _Tracer:
        def start_as_current_span(self, *args, **kwargs):
            return _SpanContextManager()

    trace_module = ModuleType("opentelemetry.trace")
    trace_module.get_tracer = lambda *args, **kwargs: _Tracer()
    trace_module.get_current_span = lambda *args, **kwargs: _Span()
    trace_module.set_tracer_provider = lambda *args, **kwargs: None

    class _SpanKind:
        INTERNAL = 0
        SERVER = 1

    class _StatusCode:
        ERROR = 1

    class _Status:
        def __init__(self, *args, **kwargs):
            return None

    trace_module.SpanKind = _SpanKind
    trace_module.Status = _Status
    trace_module.StatusCode = _StatusCode

    propagate_module = ModuleType("opentelemetry.propagate")
    propagate_module.set_global_textmap = lambda *args, **kwargs: None
    propagate_module.inject = lambda carrier, *args, **kwargs: carrier
    propagate_module.extract = lambda carrier, *args, **kwargs: {}

    otel_module.propagate = propagate_module
    otel_module.trace = trace_module

    exporter_module = ModuleType("opentelemetry.exporter.otlp.proto.http.metric_exporter")
    exporter_module.OTLPMetricExporter = lambda *args, **kwargs: None

    trace_exporter_module = ModuleType("opentelemetry.exporter.otlp.proto.http.trace_exporter")
    trace_exporter_module.OTLPSpanExporter = lambda *args, **kwargs: None

    sdk_metrics_module = ModuleType("opentelemetry.sdk.metrics")
    sdk_metrics_module.MeterProvider = lambda *args, **kwargs: None

    sdk_metrics_export_module = ModuleType("opentelemetry.sdk.metrics.export")
    sdk_metrics_export_module.PeriodicExportingMetricReader = lambda *args, **kwargs: None

    sdk_resources_module = ModuleType("opentelemetry.sdk.resources")
    sdk_resources_module.Resource = ModuleType("Resource")
    sdk_resources_module.Resource.create = lambda *args, **kwargs: None

    sdk_trace_module = ModuleType("opentelemetry.sdk.trace")

    class _TracerProvider:
        def add_span_processor(self, *args, **kwargs) -> None:
            return None

    sdk_trace_module.TracerProvider = lambda *args, **kwargs: _TracerProvider()

    sdk_trace_export_module = ModuleType("opentelemetry.sdk.trace.export")
    sdk_trace_export_module.BatchSpanProcessor = lambda *args, **kwargs: None

    trace_propagation_module = ModuleType("opentelemetry.trace.propagation.tracecontext")
    trace_propagation_module.TraceContextTextMapPropagator = lambda *args, **kwargs: None

    sys.modules["opentelemetry"] = otel_module
    sys.modules["opentelemetry.metrics"] = metrics_module
    sys.modules["opentelemetry.trace"] = trace_module
    sys.modules["opentelemetry.propagate"] = propagate_module
    sys.modules["opentelemetry.exporter.otlp.proto.http.metric_exporter"] = exporter_module
    sys.modules["opentelemetry.exporter.otlp.proto.http.trace_exporter"] = trace_exporter_module
    sys.modules["opentelemetry.sdk.metrics"] = sdk_metrics_module
    sys.modules["opentelemetry.sdk.metrics.export"] = sdk_metrics_export_module
    sys.modules["opentelemetry.sdk.resources"] = sdk_resources_module
    sys.modules["opentelemetry.sdk.trace"] = sdk_trace_module
    sys.modules["opentelemetry.sdk.trace.export"] = sdk_trace_export_module
    sys.modules["opentelemetry.trace.propagation.tracecontext"] = trace_propagation_module


def _install_security_mocks() -> None:
    import sys

    if "cryptography" in sys.modules:
        return

    cryptography_module = ModuleType("cryptography")
    hazmat_module = ModuleType("cryptography.hazmat")
    primitives_module = ModuleType("cryptography.hazmat.primitives")
    asymmetric_module = ModuleType("cryptography.hazmat.primitives.asymmetric")
    rsa_module = ModuleType("cryptography.hazmat.primitives.asymmetric.rsa")

    class RSAPublicKey:
        pass

    rsa_module.RSAPublicKey = RSAPublicKey

    sys.modules["cryptography"] = cryptography_module
    sys.modules["cryptography.hazmat"] = hazmat_module
    sys.modules["cryptography.hazmat.primitives"] = primitives_module
    sys.modules["cryptography.hazmat.primitives.asymmetric"] = asymmetric_module
    sys.modules["cryptography.hazmat.primitives.asymmetric.rsa"] = rsa_module


SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("data_lineage_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.modules[spec.name] = module
_install_opentelemetry_mocks()
_install_security_mocks()
spec.loader.exec_module(module)


def _auth_headers(monkeypatch, tenant_id: str = "tenant-a") -> dict[str, str]:
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)
    return {"X-Tenant-ID": tenant_id}


def _set_db_path(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "lineage.db"
    monkeypatch.setenv("DATA_LINEAGE_STORE_PATH", str(db_path))


def test_lineage_event_creation_and_lookup(monkeypatch, tmp_path: Path) -> None:
    _set_db_path(monkeypatch, tmp_path)
    payload = {
        "tenant_id": "tenant-a",
        "connector": "jira",
        "source": {"system": "jira", "entity": "work_item", "record_id": "WI-100"},
        "target": {"schema": "work-item", "record_id": "WI-100"},
        "transformations": ["map id -> id"],
        "timestamp": "2024-01-01T00:00:00Z",
    }

    with TestClient(module.app) as client:
        response = client.post(
            "/v1/lineage/events", json=payload, headers=_auth_headers(monkeypatch)
        )
        assert response.status_code == 200
        event = response.json()
        assert event["connector"] == "jira"
        lineage_id = event["lineage_id"]

        response = client.get(
            f"/v1/lineage/events/{lineage_id}", headers=_auth_headers(monkeypatch)
        )
        assert response.status_code == 200
        fetched = response.json()
        assert fetched["lineage_id"] == lineage_id

        response = client.get(
            "/v1/lineage/events",
            params={"connector_id": "jira"},
            headers=_auth_headers(monkeypatch),
        )
        assert response.status_code == 200
        events = response.json()
        assert len(events) == 1

        response = client.get(
            "/v1/lineage/events",
            params={"work_item_id": "WI-100"},
            headers=_auth_headers(monkeypatch),
        )
        assert response.status_code == 200
        events = response.json()
        assert len(events) == 1


def test_lineage_query_by_connector(monkeypatch, tmp_path: Path) -> None:
    _set_db_path(monkeypatch, tmp_path)
    with TestClient(module.app) as client:
        for connector in ("jira", "asana"):
            response = client.post(
                "/v1/lineage/events",
                json={
                    "tenant_id": "tenant-a",
                    "connector": connector,
                    "source": {"system": connector, "entity": "project", "record_id": "P-1"},
                    "target": {"schema": "project", "record_id": "P-1"},
                    "transformations": ["map id -> id"],
                    "timestamp": "2024-01-02T00:00:00Z",
                },
                headers=_auth_headers(monkeypatch),
            )
            assert response.status_code == 200

        response = client.get(
            "/v1/lineage/events",
            params={"connector_id": "asana"},
            headers=_auth_headers(monkeypatch),
        )
        assert response.status_code == 200
        events = response.json()
        assert len(events) == 1
        assert events[0]["connector"] == "asana"
