"""
Health Check API Routes
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from api.limiter import limiter

router = APIRouter()


@limiter.exempt
@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint for load balancers and monitoring.

    Returns:
        Basic health status of the API
    """
    from api.main import orchestrator

    checks = {
        "api": True,
        "orchestrator": orchestrator is not None and orchestrator.initialized,
    }
    status = "healthy" if all(checks.values()) else "degraded"
    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "multi-agent-ppm-platform",
        "checks": checks,
    }


@limiter.exempt
@router.get("/health/ready")
async def readiness_check(request: Request) -> dict[str, Any]:
    """
    Readiness check - indicates if the service is ready to accept traffic.

    Returns:
        Ready status including dependency checks
    """
    from api.main import orchestrator

    leader_elector = getattr(request.app.state, "leader_elector", None)
    leader_ready = leader_elector.is_leader if leader_elector else True
    checks = {
        "api": True,
        "orchestrator": orchestrator is not None and orchestrator.initialized,
        "leader": leader_ready,
    }

    all_ready = all(checks.values())
    if not all_ready:
        raise HTTPException(
            status_code=503,
            detail={
                "ready": all_ready,
                "checks": checks,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    return {
        "ready": all_ready,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@limiter.exempt
@router.get("/health/live")
async def liveness_check() -> dict[str, Any]:
    """
    Liveness check - indicates if the service is alive.

    Returns:
        Simple alive status
    """
    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
