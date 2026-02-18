from __future__ import annotations

import logging

from fastapi import FastAPI

from api.document_session_store import DocumentSessionStore, resolve_document_session_storage

logger = logging.getLogger(__name__)


def document_session_readiness(app: FastAPI) -> dict[str, str | bool]:
    store = getattr(app.state, "document_session_store", None)
    selection = getattr(app.state, "document_session_storage", None)
    return {
        "ready": store is not None,
        "storage_backend": selection.backend if selection else "unknown",
    }


async def startup_document_sessions(app: FastAPI) -> None:
    environment = app.state.environment
    document_session_storage = resolve_document_session_storage(environment=environment)
    logger.info(
        "api-gateway document session persistence configuration",
        extra={
            "environment": environment,
            "storage_backend": document_session_storage.backend,
            "durability_mode": document_session_storage.durability_mode,
            "document_session_db_path_source": document_session_storage.source,
            "document_session_db_path": str(document_session_storage.db_path),
        },
    )
    app.state.document_session_storage = document_session_storage
    app.state.document_session_store = DocumentSessionStore.from_selection(document_session_storage)


async def shutdown_document_sessions(app: FastAPI) -> None:
    document_session_store = getattr(app.state, "document_session_store", None)
    if document_session_store:
        document_session_store.close()
