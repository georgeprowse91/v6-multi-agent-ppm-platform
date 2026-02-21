from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import FastAPI

from api.secret_rotation import ConnectorSecretRotationScheduler


@dataclass(slots=True)
class SecretRotationConfig:
    enabled: bool
    interval_seconds: int
    automation_webhook_url: str | None


class SecretRotationConfigError(ValueError):
    pass


def load_secret_rotation_config(*, environ: dict[str, str] | None = None) -> SecretRotationConfig:
    env = environ or os.environ
    enabled = env.get("CONNECTOR_ROTATION_ENABLED", "false").lower() == "true"
    interval_value = env.get("CONNECTOR_ROTATION_INTERVAL_SECONDS", "3600")
    try:
        interval_seconds = int(interval_value)
    except ValueError as exc:
        raise SecretRotationConfigError(
            "CONNECTOR_ROTATION_INTERVAL_SECONDS must be an integer"
        ) from exc
    if interval_seconds <= 0:
        raise SecretRotationConfigError(
            "CONNECTOR_ROTATION_INTERVAL_SECONDS must be greater than 0"
        )
    webhook = env.get("AZURE_AUTOMATION_WEBHOOK_URL")
    return SecretRotationConfig(
        enabled=enabled,
        interval_seconds=interval_seconds,
        automation_webhook_url=webhook,
    )


def secret_rotation_readiness(app: FastAPI) -> dict[str, bool | str]:
    scheduler = getattr(app.state, "rotation_scheduler", None)
    config = getattr(app.state, "secret_rotation_config", None)
    if config is None:
        return {"ready": False, "enabled": False, "detail": "config_missing"}
    if not config.enabled:
        return {"ready": True, "enabled": False, "detail": "disabled"}
    return {
        "ready": scheduler is not None,
        "enabled": True,
        "detail": "running" if scheduler is not None else "not_started",
    }


async def startup_secret_rotation(app: FastAPI) -> None:
    config = load_secret_rotation_config()
    app.state.secret_rotation_config = config
    if not config.enabled:
        return
    scheduler = ConnectorSecretRotationScheduler(
        app.state.connector_config_store,
        interval_seconds=config.interval_seconds,
        automation_webhook_url=config.automation_webhook_url,
    )
    scheduler.start()
    app.state.rotation_scheduler = scheduler


async def shutdown_secret_rotation(app: FastAPI) -> None:
    scheduler = getattr(app.state, "rotation_scheduler", None)
    if scheduler:
        scheduler.stop()
