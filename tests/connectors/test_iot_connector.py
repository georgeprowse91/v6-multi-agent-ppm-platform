from __future__ import annotations

import contextlib
import sys
import types
from pathlib import Path
from typing import Any

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

import http_client as http_client_module
from base_connector import ConnectionStatus, ConnectorCategory, ConnectorConfig
from iot_connector import IoTConnector


class DummySpan:
    def set_attribute(self, *_args: object, **_kwargs: object) -> None:
        return None

    def set_status(self, *_args: object, **_kwargs: object) -> None:
        return None

    def record_exception(self, *_args: object, **_kwargs: object) -> None:
        return None


class DummyTracer:
    def start_span(self, *_args: object, **_kwargs: object) -> DummySpan:
        return DummySpan()


@contextlib.contextmanager
def _noop_use_span(span: DummySpan, end_on_exit: bool = True) -> DummySpan:
    yield span


http_client_module.tracer = DummyTracer()
http_client_module.trace.use_span = _noop_use_span
http_client_module.SpanKind = types.SimpleNamespace(CLIENT="client")


def _build_transport(routes: dict[tuple[str, str], tuple[int, Any]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        if key in routes:
            status, payload = routes[key]
            return httpx.Response(status, json=payload)
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IOT_DEVICE_ENDPOINT", "https://iot.example.com")
    monkeypatch.setenv("IOT_AUTH_TOKEN", "test-token")


def test_iot_authenticate_success() -> None:
    transport = _build_transport({("GET", "/health"): (200, {"status": "ok"})})
    config = ConnectorConfig(
        connector_id="iot",
        name="IoT Integrations",
        category=ConnectorCategory.IOT,
    )
    connector = IoTConnector(config, transport=transport)

    assert connector.authenticate() is True


def test_iot_read_sensor_data() -> None:
    transport = _build_transport(
        {
            ("GET", "/health"): (200, {"status": "ok"}),
            ("GET", "/sensors/data"): (200, {"items": [{"id": "reading-1"}]}),
        }
    )
    config = ConnectorConfig(
        connector_id="iot",
        name="IoT Integrations",
        category=ConnectorCategory.IOT,
    )
    connector = IoTConnector(config, transport=transport)

    result = connector.read("sensor_data")

    # The real IoT connector normalises raw records into a standard format;
    # the original record lands in the `metadata` field.
    assert len(result) == 1
    assert result[0]["source"] == "iot"
    assert result[0]["metadata"] == {"id": "reading-1"}


def test_iot_test_connection_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    transport = httpx.MockTransport(handler)
    config = ConnectorConfig(
        connector_id="iot",
        name="IoT Integrations",
        category=ConnectorCategory.IOT,
    )
    connector = IoTConnector(config, transport=transport)

    result = connector.test_connection()

    assert result.status == ConnectionStatus.TIMEOUT
