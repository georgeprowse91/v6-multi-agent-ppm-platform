from __future__ import annotations

from typing import Any

from fastapi import Request


def get_orchestrator(request: Request) -> Any:
    return request.app.state.orchestrator


def get_connector_config_store(request: Request) -> Any:
    return request.app.state.connector_config_store


def get_project_connector_config_store(request: Request) -> Any:
    return request.app.state.project_connector_config_store


def get_webhook_store(request: Request) -> Any:
    return request.app.state.webhook_store


def get_circuit_breaker(request: Request) -> Any:
    return request.app.state.connector_circuit_breaker


def get_document_session_store(request: Request) -> Any:
    return request.app.state.document_session_store
