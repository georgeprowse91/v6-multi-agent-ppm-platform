"""
Agent API Routes
"""

import logging
from typing import Any

from common.exceptions import PPMPlatformError, exception_to_http_status
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

from agents.runtime import AgentResponse

router = APIRouter()
logger = logging.getLogger(__name__)


class AgentQueryErrorResponse(BaseModel):
    """Client-safe error response for query failures."""

    error: str = "AgentQueryError"
    message: str
    correlation_id: str | None = None


DOMAIN_ERROR_MESSAGES: dict[int, str] = {
    400: "Invalid query request",
    401: "Authentication required",
    403: "Insufficient permissions for query",
    404: "Requested resource not found",
    409: "Query could not be processed due to a conflict",
    429: "Query rate limit exceeded",
    502: "Dependent service failed while processing query",
    503: "Agent service is temporarily unavailable",
}


def _get_correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None) or request.headers.get("X-Correlation-ID")


def _raise_query_error(status_code: int, message: str, correlation_id: str | None) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=AgentQueryErrorResponse(message=message, correlation_id=correlation_id).model_dump(),
    )


class QueryRequest(BaseModel):
    """Request model for agent queries."""

    query: str
    context: dict[str, Any] | None = None
    prompt: dict[str, Any] | None = None


@router.post(
    "/query",
    response_model=AgentResponse,
    responses={
        400: {"model": AgentQueryErrorResponse},
        401: {"model": AgentQueryErrorResponse},
        403: {"model": AgentQueryErrorResponse},
        404: {"model": AgentQueryErrorResponse},
        409: {"model": AgentQueryErrorResponse},
        429: {"model": AgentQueryErrorResponse},
        500: {"model": AgentQueryErrorResponse},
        502: {"model": AgentQueryErrorResponse},
        503: {"model": AgentQueryErrorResponse},
    },
)
async def process_query(request: QueryRequest, http_request: Request) -> AgentResponse:
    """
    Process a natural language query through the agent system.

    This endpoint routes the query through the Intent Router and Response Orchestration agents.
    """
    import sys

    _main = sys.modules.get("api.main")
    orchestrator = getattr(_main, "orchestrator", None) or getattr(
        http_request.app.state, "orchestrator", None
    )
    correlation_id = _get_correlation_id(http_request)

    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        result = await orchestrator.process_query(
            query=request.query,
            context=request.context,
            prompt=request.prompt,
        )
        return AgentResponse.model_validate(result)

    except ValidationError as exc:
        logger.exception(
            "Agent query response validation failed (correlation_id=%s)", correlation_id
        )
        raise HTTPException(status_code=500, detail="Invalid agent response") from exc
    except PPMPlatformError as exc:
        status_code = exception_to_http_status(exc)
        message = DOMAIN_ERROR_MESSAGES.get(status_code, "Unable to process query")
        logger.exception(
            "Agent query domain failure (correlation_id=%s, status_code=%s)",
            correlation_id,
            status_code,
        )
        _raise_query_error(status_code=status_code, message=message, correlation_id=correlation_id)
    except (RuntimeError, ValueError):
        logger.exception("Agent query processing failed (correlation_id=%s)", correlation_id)
        _raise_query_error(
            status_code=500,
            message="Unable to process query",
            correlation_id=correlation_id,
        )


@router.get("/agents")
async def list_agents(request: Request) -> dict[str, Any]:
    """
    List all available agents.

    Returns information about all loaded agents and their capabilities.
    """
    import sys

    _main = sys.modules.get("api.main")
    orchestrator = getattr(_main, "orchestrator", None) or getattr(
        request.app.state, "orchestrator", None
    )

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    return {
        "total_agents": orchestrator.get_agent_count(),
        "agents": orchestrator.list_agents(),
    }


@router.get("/agents/{agent_id}")
async def get_agent_info(agent_id: str, request: Request) -> dict[str, Any]:
    """
    Get information about a specific agent.
    """
    import sys

    _main = sys.modules.get("api.main")
    orchestrator = getattr(_main, "orchestrator", None) or getattr(
        request.app.state, "orchestrator", None
    )

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    return {
        "agent_id": agent_id,
        "capabilities": agent.get_capabilities(),
        "initialized": agent.initialized,
    }
