"""
Multi-Agent PPM Platform - FastAPI Application

This is the main entry point for the PPM platform REST API.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.limiter import limiter
from api.middleware.security import AuthTenantMiddleware, FieldMaskingMiddleware
from api.routes import agents, health, agent_config
from api.runtime_bootstrap import bootstrap_runtime_paths

REPO_ROOT = Path(__file__).resolve().parents[4]
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for path_root in (REPO_ROOT, OBSERVABILITY_ROOT):
    if str(path_root) not in sys.path:
        sys.path.insert(0, str(path_root))

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Multi-Agent PPM Platform",
    description="AI-native Project Portfolio Management platform with 25 specialized agents",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


def _version_payload() -> dict[str, str]:
    return {
        "service": "multi-agent-ppm-api",
        "version": os.getenv("APP_VERSION", app.version),
        "build_sha": os.getenv("BUILD_SHA", "unknown"),
    }


environment = os.getenv("ENVIRONMENT", "development").lower()

# Configure CORS
allowed_origins_env = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8501,http://localhost:8000"
)
allowed_origins = (
    ["*"]
    if allowed_origins_env.strip() == "*"
    else [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
)
if "*" in allowed_origins and environment not in {"dev", "development", "local", "test"}:
    raise RuntimeError("Wildcard CORS origins are not permitted outside development environments.")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(AuthTenantMiddleware)
app.add_middleware(FieldMaskingMiddleware)
configure_tracing("api-gateway")
configure_metrics("api-gateway")
app.add_middleware(TraceMiddleware, service_name="api-gateway")
app.add_middleware(RequestMetricsMiddleware, service_name="api-gateway")

# Global orchestrator instance
orchestrator = None


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    global orchestrator
    logger.info("Starting Multi-Agent PPM Platform...")

    # Initialize orchestrator
    bootstrap_runtime_paths()
    from orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator()
    await orchestrator.initialize()

    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global orchestrator
    logger.info("Shutting down Multi-Agent PPM Platform...")

    if orchestrator:
        await orchestrator.cleanup()

    logger.info("Application shut down successfully")


@limiter.exempt
@app.get("/healthz")
async def healthz():
    """Lightweight health check for local dev and probes."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", app.version),
    }


@limiter.exempt
@app.get("/version")
async def version():
    """Return API version metadata."""
    return _version_payload()


@limiter.exempt
@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Multi-Agent PPM Platform API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/api/docs",
    }


@app.get("/api/v1/status")
async def get_status():
    """Get platform status."""
    return {
        "status": "healthy",
        "orchestrator_initialized": orchestrator is not None and orchestrator.initialized,
        "agents_loaded": orchestrator.get_agent_count() if orchestrator else 0,
    }


# Include routers
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(agent_config.router, prefix="/api/v1", tags=["agent-config"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all uncaught exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
