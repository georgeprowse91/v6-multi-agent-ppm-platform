from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from api.routes.agents import process_query, QueryRequest
from common.exceptions import ResourceNotFoundError


@pytest.mark.asyncio
async def test_process_query_runtime_error_is_sanitized_and_logs_with_correlation_id(caplog):
    caplog.set_level("ERROR")
    secret_message = "db password=super-secret"
    orchestrator = MagicMock(initialized=True)
    orchestrator.process_query = AsyncMock(side_effect=RuntimeError(secret_message))

    http_request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(orchestrator=orchestrator)),
        state=SimpleNamespace(correlation_id="corr-123"),
        headers={},
    )

    with pytest.raises(HTTPException) as exc_info:
        await process_query(QueryRequest(query="status update"), http_request)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == {
        "error": "AgentQueryError",
        "message": "Unable to process query",
        "correlation_id": "corr-123",
    }
    assert secret_message not in str(exc_info.value.detail)
    assert "corr-123" in caplog.text
    assert secret_message in caplog.text


@pytest.mark.asyncio
async def test_process_query_domain_exception_maps_status_and_hides_sensitive_text(caplog):
    caplog.set_level("ERROR")
    sensitive_message = "customer SSN leaked"
    orchestrator = MagicMock(initialized=True)
    orchestrator.process_query = AsyncMock(side_effect=ResourceNotFoundError(sensitive_message))

    http_request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(orchestrator=orchestrator)),
        state=SimpleNamespace(),
        headers={"X-Correlation-ID": "corr-404"},
    )

    with pytest.raises(HTTPException) as exc_info:
        await process_query(QueryRequest(query="find project"), http_request)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == {
        "error": "AgentQueryError",
        "message": "Requested resource not found",
        "correlation_id": "corr-404",
    }
    assert sensitive_message not in str(exc_info.value.detail)
    assert "corr-404" in caplog.text
    assert sensitive_message in caplog.text
