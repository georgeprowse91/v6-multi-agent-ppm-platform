from __future__ import annotations

from types import SimpleNamespace

import pytest
from api.bootstrap.components import build_default_bootstrap_registry
from api.bootstrap.registry import BootstrapRegistry, StartupComponent, StartupFailure
from api.bootstrap.secret_rotation_component import (
    SecretRotationConfigError,
    load_secret_rotation_config,
)
from api.routes import health
from fastapi import HTTPException


@pytest.mark.anyio
async def test_default_registry_registration_contains_expected_components():
    registry = build_default_bootstrap_registry()

    components = registry.components

    assert set(components) == {
        "orchestrator",
        "connector_resources",
        "document_sessions",
        "secret_rotation",
        "leader_election",
    }
    assert components["document_sessions"].dependencies == ("orchestrator",)
    assert components["secret_rotation"].dependencies == ("connector_resources",)
    assert components["secret_rotation"].required is False


@pytest.mark.anyio
async def test_startup_failure_reports_component_and_order():
    events: list[str] = []
    app = SimpleNamespace(state=SimpleNamespace())
    registry = BootstrapRegistry()

    async def _start_a(_app):
        events.append("start:a")

    async def _stop_a(_app):
        events.append("stop:a")

    async def _start_b(_app):
        events.append("start:b")
        raise RuntimeError("boom")

    async def _stop_b(_app):
        events.append("stop:b")

    registry.register(StartupComponent(name="a", startup=_start_a, shutdown=_stop_a))
    registry.register(
        StartupComponent(name="b", startup=_start_b, shutdown=_stop_b, dependencies=("a",))
    )

    with pytest.raises(StartupFailure) as exc_info:
        await registry.startup(app)

    assert exc_info.value.component == "b"
    assert exc_info.value.startup_order == ["a"]
    assert "boom" in exc_info.value.message
    assert events == ["start:a", "start:b", "stop:a"]


@pytest.mark.anyio
async def test_shutdown_runs_reverse_startup_order_for_clean_teardown():
    events: list[str] = []
    app = SimpleNamespace(state=SimpleNamespace())
    registry = BootstrapRegistry()

    async def _start_a(_app):
        events.append("start:a")

    async def _stop_a(_app):
        events.append("stop:a")

    async def _start_b(_app):
        events.append("start:b")

    async def _stop_b(_app):
        events.append("stop:b")

    registry.register(StartupComponent(name="a", startup=_start_a, shutdown=_stop_a))
    registry.register(
        StartupComponent(
            name="b",
            startup=_start_b,
            shutdown=_stop_b,
            dependencies=("a",),
        )
    )

    await registry.startup(app)
    await registry.shutdown(app)

    assert events == ["start:a", "start:b", "stop:b", "stop:a"]


@pytest.mark.anyio
async def test_health_readiness_reports_component_level_status():
    component_payload = {
        "orchestrator": {"ready": True, "required": True},
        "secret_rotation": {"ready": False, "required": False},
    }

    class _Registry:
        def readiness(self, _app):
            return component_payload

    app = SimpleNamespace(state=SimpleNamespace(bootstrap_registry=_Registry()))
    request = SimpleNamespace(app=app)

    payload = await health.readiness_check(request)

    assert payload["ready"] is True
    assert payload["checks"] == {"orchestrator": True, "secret_rotation": False}
    assert payload["components"] == component_payload


@pytest.mark.anyio
async def test_health_readiness_fails_when_required_component_not_ready():
    component_payload = {
        "orchestrator": {"ready": False, "required": True},
        "secret_rotation": {"ready": True, "required": False},
    }

    class _Registry:
        def readiness(self, _app):
            return component_payload

    app = SimpleNamespace(state=SimpleNamespace(bootstrap_registry=_Registry()))
    request = SimpleNamespace(app=app)

    with pytest.raises(HTTPException) as exc_info:
        await health.readiness_check(request)

    assert exc_info.value.status_code == 503
    detail = exc_info.value.detail
    assert detail["checks"]["orchestrator"] is False
    assert detail["components"] == component_payload


def test_secret_rotation_config_validation_rejects_invalid_interval():
    with pytest.raises(SecretRotationConfigError):
        load_secret_rotation_config(
            environ={
                "CONNECTOR_ROTATION_ENABLED": "true",
                "CONNECTOR_ROTATION_INTERVAL_SECONDS": "not-int",
            }
        )


def test_secret_rotation_config_loads_disabled_by_default():
    config = load_secret_rotation_config(environ={})

    assert config.enabled is False
    assert config.interval_seconds == 3600
    assert config.automation_webhook_url is None
