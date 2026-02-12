"""Tests for MCP connector fallback exception handling."""

from __future__ import annotations

import httpx
import pytest

from integrations.connectors.integration.framework import IntegrationConfig
from integrations.connectors.integration.mcp_connectors import PlanviewMcpConnector


class _RaisingRestConnector:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def fetch(self, endpoint: str):  # noqa: ANN202
        raise self._error

    def post(self, endpoint: str, payload):  # noqa: ANN001, ANN202
        raise self._error


class _OkRestConnector:
    def post(self, endpoint: str, payload):  # noqa: ANN001, ANN202
        return {"status": "ok", "endpoint": endpoint, "payload": payload}


def _config() -> IntegrationConfig:
    return IntegrationConfig(system="planview", base_url="https://planview.example.com")


def test_fallback_list_maps_httpx_error_to_empty_result() -> None:
    connector = PlanviewMcpConnector(
        _config(),
        rest_connector=_RaisingRestConnector(httpx.HTTPError("boom")),
    )

    result = connector._fallback_list("projects")

    assert result == []


def test_fallback_list_propagates_unexpected_exceptions() -> None:
    connector = PlanviewMcpConnector(
        _config(),
        rest_connector=_RaisingRestConnector(RuntimeError("unexpected")),
    )

    with pytest.raises(RuntimeError, match="unexpected"):
        connector._fallback_list("projects")


def test_fallback_create_maps_httpx_error_to_failed_status() -> None:
    connector = PlanviewMcpConnector(
        _config(),
        rest_connector=_RaisingRestConnector(httpx.HTTPError("down")),
    )

    result = connector._fallback_create("work_items", {"id": "1"})

    assert result == {"status": "failed", "reason": "down"}


def test_fallback_create_propagates_unexpected_exceptions() -> None:
    connector = PlanviewMcpConnector(
        _config(),
        rest_connector=_RaisingRestConnector(RuntimeError("unexpected-create")),
    )

    with pytest.raises(RuntimeError, match="unexpected-create"):
        connector._fallback_create("work_items", {"id": "1"})


def test_fallback_create_returns_rest_response_on_success() -> None:
    connector = PlanviewMcpConnector(_config(), rest_connector=_OkRestConnector())

    result = connector._fallback_create("work_items", {"id": "1"})

    assert result["status"] == "ok"


class _RuntimeAuthConnector(PlanviewMcpConnector):
    def authenticate(self) -> bool:
        raise RuntimeError("known-auth")


class _UnexpectedAuthConnector(PlanviewMcpConnector):
    def authenticate(self) -> bool:
        raise KeyError("unknown-auth")


def test_health_check_maps_known_errors_to_false() -> None:
    connector = _RuntimeAuthConnector(_config())

    assert connector.health_check() is False


def test_health_check_propagates_unknown_exceptions() -> None:
    connector = _UnexpectedAuthConnector(_config())

    with pytest.raises(KeyError, match="unknown-auth"):
        connector.health_check()
