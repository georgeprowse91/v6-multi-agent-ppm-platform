"""
Tests for the IoT Connector

Uses mocked HTTP transport to validate configuration, connection tests,
and sensor data ingestion.
"""

from __future__ import annotations

import contextlib
import sys
import types
from pathlib import Path
from typing import Any

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CONNECTOR_SDK_PATH = REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"
IOT_CONNECTOR_PATH = REPO_ROOT / "integrations" / "connectors" / "iot" / "src"
for path in (CONNECTOR_SDK_PATH, IOT_CONNECTOR_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

if "opentelemetry" not in sys.modules:
    otel_module = types.ModuleType("opentelemetry")
    trace_module = types.ModuleType("opentelemetry.trace")

    class DummySpan:
        def set_attribute(self, *_args, **_kwargs) -> None:
            return None

        def set_status(self, *_args, **_kwargs) -> None:
            return None

        def record_exception(self, *_args, **_kwargs) -> None:
            return None

    class DummyTracer:
        def start_span(self, *_args, **_kwargs) -> DummySpan:
            return DummySpan()

    class DummySpanKind:
        CLIENT = "client"

    class DummyStatus:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

    class DummyStatusCode:
        ERROR = "error"

    def get_tracer(_name: str) -> DummyTracer:
        return DummyTracer()

    @contextlib.contextmanager
    def use_span(_span: DummySpan, end_on_exit: bool = True):  # noqa: ARG001
        yield

    trace_module.get_tracer = get_tracer  # type: ignore[attr-defined]
    trace_module.use_span = use_span  # type: ignore[attr-defined]
    trace_module.SpanKind = DummySpanKind  # type: ignore[attr-defined]
    trace_module.Status = DummyStatus  # type: ignore[attr-defined]
    trace_module.StatusCode = DummyStatusCode  # type: ignore[attr-defined]
    otel_module.trace = trace_module  # type: ignore[attr-defined]
    sys.modules["opentelemetry"] = otel_module
    sys.modules["opentelemetry.trace"] = trace_module

from base_connector import ConnectionStatus, ConnectorCategory, ConnectorConfig
from iot_connector import IoTConnector


class MockTransport(httpx.BaseTransport):
    """Mock HTTP transport for testing."""

    def __init__(self, responses: dict[str, Any] | None = None):
        self._responses = responses or {}
        self._requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self._requests.append(request)
        url_path = request.url.path
        for path_pattern, response_data in self._responses.items():
            if path_pattern in url_path:
                status_code = response_data.get("status_code", 200)
                content = response_data.get("content", {})
                return httpx.Response(status_code=status_code, json=content, request=request)
        return httpx.Response(status_code=404, json={"error": "Not found"}, request=request)


@pytest.fixture
def iot_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="iot",
        name="IoT Integrations",
        category=ConnectorCategory.IOT,
        instance_url="https://iot.example.com",
        custom_fields={
            "protocol": "http",
            "device_endpoint": "https://iot.example.com",
            "auth_token": "test-token",
            "device_ids": "device-1,device-2",
        },
    )


def test_connection_invalid_config() -> None:
    config = ConnectorConfig(
        connector_id="iot",
        name="IoT Integrations",
        category=ConnectorCategory.IOT,
        custom_fields={"protocol": "http"},
    )
    connector = IoTConnector(config)
    result = connector.test_connection()
    assert result.status == ConnectionStatus.INVALID_CONFIG


def test_connection_success_http(iot_config: ConnectorConfig) -> None:
    transport = MockTransport(
        {
            "/health": {"status_code": 200, "content": {"status": "ok"}},
        }
    )
    connector = IoTConnector(iot_config, transport=transport)
    result = connector.test_connection()
    assert result.status == ConnectionStatus.CONNECTED


def test_connection_unauthorized_http(iot_config: ConnectorConfig) -> None:
    transport = MockTransport(
        {
            "/health": {"status_code": 401, "content": {"error": "unauthorized"}},
        }
    )
    connector = IoTConnector(iot_config, transport=transport)
    result = connector.test_connection()
    assert result.status == ConnectionStatus.UNAUTHORIZED


def test_ingest_sensor_data_normalizes_records(iot_config: ConnectorConfig) -> None:
    transport = MockTransport(
        {
            "/health": {"status_code": 200, "content": {"status": "ok"}},
            "/sensors/data": {
                "status_code": 200,
                "content": {
                    "items": [
                        {
                            "deviceId": "device-1",
                            "sensorType": "temperature",
                            "measurement": 72.5,
                            "units": "F",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "location": "lab-1",
                        }
                    ]
                },
            },
        }
    )
    connector = IoTConnector(iot_config, transport=transport)
    records = connector.read("sensor_data")
    assert records == [
        {
            "source": "iot",
            "device_id": "device-1",
            "sensor_type": "temperature",
            "value": 72.5,
            "unit": "F",
            "observed_at": "2024-01-01T00:00:00Z",
            "metadata": {"location": "lab-1"},
        }
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
