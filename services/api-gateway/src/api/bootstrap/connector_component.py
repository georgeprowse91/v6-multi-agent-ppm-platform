from __future__ import annotations

from fastapi import FastAPI

from api.routes.connectors import (
    build_circuit_breaker,
    build_config_store,
    build_project_config_store,
    build_webhook_store,
)


def connector_readiness(_app: FastAPI) -> dict[str, bool]:
    return {"ready": True}


async def startup_connector_resources(app: FastAPI) -> None:
    app.state.connector_config_store = build_config_store()
    app.state.project_connector_config_store = build_project_config_store()
    app.state.webhook_store = build_webhook_store()
    app.state.connector_circuit_breaker = build_circuit_breaker()


async def shutdown_connector_resources(_app: FastAPI) -> None:
    return None
