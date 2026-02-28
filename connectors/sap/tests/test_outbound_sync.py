import logging
import sys
import types

from fastapi.testclient import TestClient

if "opentelemetry" not in sys.modules:
    opentelemetry = types.ModuleType("opentelemetry")
    trace_module = types.ModuleType("opentelemetry.trace")

    class _Span:
        def set_attribute(self, *args, **kwargs):
            return None

        def set_status(self, *args, **kwargs):
            return None

        def record_exception(self, *args, **kwargs):
            return None

    class _SpanContext:
        def __enter__(self):
            return _Span()

        def __exit__(self, exc_type, exc, tb):
            return False

    class _DummyTracer:
        def start_span(self, *args, **kwargs):
            return _Span()

        def start_as_current_span(self, *args, **kwargs):
            return _SpanContext()

    class _DummyUseSpan:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    trace_module.get_tracer = lambda name: _DummyTracer()
    trace_module.use_span = lambda span, end_on_exit=True: _DummyUseSpan()
    trace_module.SpanKind = types.SimpleNamespace(CLIENT="CLIENT", INTERNAL="INTERNAL")
    trace_module.Status = lambda code: code
    trace_module.StatusCode = types.SimpleNamespace(ERROR="ERROR")

    opentelemetry.trace = trace_module
    sys.modules["opentelemetry"] = opentelemetry
    sys.modules["opentelemetry.trace"] = trace_module


if "observability" not in sys.modules:
    observability_pkg = types.ModuleType("observability")
    logging_module = types.ModuleType("observability.logging")
    metrics_module = types.ModuleType("observability.metrics")
    tracing_module = types.ModuleType("observability.tracing")

    logging_module.configure_logging = lambda service_name: None

    class _DummyMeter:
        def create_histogram(self, *args, **kwargs):
            return types.SimpleNamespace(record=lambda *a, **k: None)

        def create_counter(self, *args, **kwargs):
            return types.SimpleNamespace(add=lambda *a, **k: None)

    metrics_module.configure_metrics = lambda service_name: _DummyMeter()
    tracing_module.configure_tracing = lambda service_name: None

    sys.modules["observability"] = observability_pkg
    sys.modules["observability.logging"] = logging_module
    sys.modules["observability.metrics"] = metrics_module
    sys.modules["observability.tracing"] = tracing_module

if "jsonschema" not in sys.modules:
    jsonschema = types.ModuleType("jsonschema")

    class _Draft202012Validator:
        def __init__(self, *args, **kwargs):
            return None

        def iter_errors(self, *args, **kwargs):
            return []

    class _FormatChecker:
        pass

    jsonschema.Draft202012Validator = _Draft202012Validator
    jsonschema.FormatChecker = _FormatChecker
    sys.modules["jsonschema"] = jsonschema

from connectors.sap.src.main import SapConfig, app, send_to_external_system


def test_sap_outbound_sync(monkeypatch, caplog):
    caplog.set_level(logging.INFO)

    # Mock the outbound hook to prevent real logging or API calls
    def mock_send(records, tenant_id, *, include_schema):
        assert tenant_id == "test-tenant"
        assert isinstance(records, list)

    monkeypatch.setattr("connectors.sap.src.main.send_to_external_system", mock_send)

    client = TestClient(app)
    payload = {
        "records": [{"id": "123", "name": "Example"}],
        "tenant_id": "test-tenant",
        "live": True,
        "include_schema": False,
    }
    response = client.post("/connectors/sap/sync/outbound", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_send_to_external_system_posts_mapped_sap_keys(monkeypatch):
    posted_payloads: list[dict[str, object]] = []

    class FakeClient:
        def post(self, endpoint, *, params=None, json=None):
            posted_payloads.append(json)

        def close(self):
            return None

    monkeypatch.setattr(
        "connectors.sap.src.main.SapConfig.from_env",
        classmethod(lambda cls, rate_limit_per_minute: SapConfig("https://sap.example", "u", "p", "100", 120)),
    )
    monkeypatch.setattr("connectors.sap.src.main._build_client", lambda config: FakeClient())

    send_to_external_system(
        [
            {
                "id": "P-500",
                "name": "Mapped Outbound",
                "status": "active",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        ],
        "tenant-1",
        include_schema=False,
    )

    assert len(posted_payloads) == 1
    posted = posted_payloads[0]
    assert "ProjectID" in posted
    assert "Description" in posted
    assert "LifecycleStatus" in posted
    assert "id" not in posted
    assert "name" not in posted
    assert "status" not in posted
