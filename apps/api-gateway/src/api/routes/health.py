"""
Health Check API Routes
"""

from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.

    Returns:
        Basic health status of the API
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "multi-agent-ppm-platform",
    }


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check - indicates if the service is ready to accept traffic.

    Returns:
        Ready status including dependency checks
    """
    from api.main import orchestrator

    checks = {
        "api": True,
        "orchestrator": orchestrator is not None and orchestrator.initialized,
    }

    all_ready = all(checks.values())

    return {
        "ready": all_ready,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check - indicates if the service is alive.

    Returns:
        Simple alive status
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
    }
