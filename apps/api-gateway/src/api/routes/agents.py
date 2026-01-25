"""
Agent API Routes
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for agent queries."""

    query: str
    context: dict[str, Any] | None = None


class QueryResponse(BaseModel):
    """Response model for agent queries."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query through the agent system.

    This endpoint routes the query through the Intent Router and Response Orchestration agents.
    """
    from api.main import orchestrator

    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        result = await orchestrator.process_query(
            query=request.query,
            context=request.context,
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agents():
    """
    List all available agents.

    Returns information about all loaded agents and their capabilities.
    """
    from api.main import orchestrator

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    return {
        "total_agents": orchestrator.get_agent_count(),
        "agents": orchestrator.list_agents(),
    }


@router.get("/agents/{agent_id}")
async def get_agent_info(agent_id: str):
    """
    Get information about a specific agent.
    """
    from api.main import orchestrator

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
