from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"
SDK_PATH_STR = str(SDK_PATH.resolve())
if SDK_PATH_STR not in sys.path:
    sys.path.insert(0, SDK_PATH_STR)

from base_connector import (  # noqa: E402
    BaseConnector,
    CircuitBreakerOpenError,
    ConnectionStatus,
    ConnectionTestResult,
    ConnectorCallFailedError,
    ConnectorCategory,
    ConnectorConfig,
    ConnectorSchemaValidationError,
)


class DummyConnector(BaseConnector):
    CONNECTOR_ID = "dummy"
    CONNECTOR_NAME = "Dummy"

    def __init__(self, config: ConnectorConfig, results: list[Any], **kwargs: Any) -> None:
        super().__init__(config, **kwargs)
        self._results = list(results)

    def authenticate(self) -> bool:
        return True

    def test_connection(self) -> ConnectionTestResult:
        return ConnectionTestResult(status=ConnectionStatus.CONNECTED, message="ok")

    def read(
        self,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return []

    def _execute_call(
        self, endpoint: str, payload: dict[str, Any], *, timeout: float
    ) -> dict[str, Any]:
        if not self._results:
            return {"endpoint": endpoint, "payload": payload, "timeout": timeout}
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _config() -> ConnectorConfig:
    return ConnectorConfig(connector_id="dummy", name="Dummy", category=ConnectorCategory.PM)


def test_call_valid_request_succeeds() -> None:
    connector = DummyConnector(_config(), results=[{"ok": True}], max_retries=1)
    schema = {
        "request": {
            "type": "object",
            "properties": {"foo": {"type": "string"}},
            "required": ["foo"],
        },
        "response": {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
    }

    response = connector.call("/test", {"foo": "bar"}, schema=schema)

    assert response == {"ok": True}


def test_call_invalid_schema_raises_validation_error() -> None:
    connector = DummyConnector(_config(), results=[{"ok": True}])
    request_schema = {
        "request": {
            "type": "object",
            "properties": {"foo": {"type": "string"}},
            "required": ["foo"],
        }
    }

    with pytest.raises(ConnectorSchemaValidationError):
        connector.call("/test", {"bar": "missing required key"}, schema=request_schema)


def test_call_invalid_response_schema_raises_validation_error() -> None:
    connector = DummyConnector(_config(), results=[{"ok": "yes"}])
    schema = {
        "response": {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        }
    }

    with pytest.raises(ConnectorCallFailedError) as exc:
        connector.call("/test", {"foo": "bar"}, schema=schema)

    assert isinstance(exc.value.__cause__, ConnectorSchemaValidationError)


def test_call_timeout_retries_and_fails() -> None:
    connector = DummyConnector(
        _config(),
        results=[TimeoutError("timeout"), TimeoutError("timeout"), TimeoutError("timeout")],
        max_retries=2,
        retry_initial_delay_seconds=0.001,
    )

    with pytest.raises(ConnectorCallFailedError):
        connector.call("/slow", {"foo": "bar"})


def test_circuit_breaker_opens_after_consecutive_failures() -> None:
    connector = DummyConnector(
        _config(),
        results=[ValueError("boom")] * 10,
        max_retries=0,
        retry_initial_delay_seconds=0.001,
        circuit_failure_threshold=3,
        circuit_failure_window_seconds=60,
        circuit_recovery_timeout_seconds=120,
    )

    for _ in range(3):
        with pytest.raises(ConnectorCallFailedError):
            connector.call("/fail", {"foo": "bar"})

    with pytest.raises(CircuitBreakerOpenError):
        connector.call("/fail", {"foo": "bar"})
