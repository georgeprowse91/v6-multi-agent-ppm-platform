"""
Multi-Agent PPM Platform - FastAPI Application

This is the main entry point for the PPM platform REST API.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.leader_election import build_leader_elector
from api.limiter import limiter
from api.middleware.security import AuthTenantMiddleware, FieldMaskingMiddleware
from api.routes import (
    agent_config,
    agents,
    analytics,
    audit,
    certifications,
    compliance_research,
    connectors,
    documents,
    health,
    lineage,
    risk_research,
    scope_research,
    vendor_management,
    vendor_research,
    workflows,
)
from api.runtime_bootstrap import bootstrap_runtime_paths

REPO_ROOT = Path(__file__).resolve().parents[4]
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
for path_root in (REPO_ROOT, OBSERVABILITY_ROOT, SECURITY_ROOT):
    if str(path_root) not in sys.path:
        sys.path.insert(0, str(path_root))

from packages.version import API_VERSION  # noqa: E402
from observability.logging import configure_logging  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.errors import register_error_handlers  # noqa: E402
from security.headers import SecurityHeadersMiddleware  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Multi-Agent PPM Platform",
    description="AI-native Project Portfolio Management platform with 25 specialized agents",
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_prefix="/v1",
)


def _version_payload() -> dict[str, str]:
    return {
        "service": "multi-agent-ppm-api",
        "api_version": API_VERSION,
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
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(AuthTenantMiddleware)
app.add_middleware(FieldMaskingMiddleware)
configure_tracing("api-gateway")
configure_metrics("api-gateway")
configure_logging("api-gateway")
app.add_middleware(TraceMiddleware, service_name="api-gateway")
app.add_middleware(RequestMetricsMiddleware, service_name="api-gateway")
register_error_handlers(app)

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
    app.state.orchestrator = orchestrator

    app.state.leader_elector = build_leader_elector("api-gateway")
    app.state.leader_elector.start()

    rotation_enabled = os.getenv("CONNECTOR_ROTATION_ENABLED", "false").lower() == "true"
    if rotation_enabled:
        from api.routes.connectors import get_config_store
        from api.secret_rotation import ConnectorSecretRotationScheduler

        interval = int(os.getenv("CONNECTOR_ROTATION_INTERVAL_SECONDS", "3600"))
        webhook_url = os.getenv("AZURE_AUTOMATION_WEBHOOK_URL")
        scheduler = ConnectorSecretRotationScheduler(
            get_config_store(),
            interval_seconds=interval,
            automation_webhook_url=webhook_url,
        )
        scheduler.start()
        app.state.rotation_scheduler = scheduler

    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global orchestrator
    logger.info("Shutting down Multi-Agent PPM Platform...")

    if orchestrator:
        await orchestrator.cleanup()

    leader_elector = getattr(app.state, "leader_elector", None)
    if leader_elector:
        leader_elector.stop()

    rotation_scheduler = getattr(app.state, "rotation_scheduler", None)
    if rotation_scheduler:
        rotation_scheduler.stop()

    logger.info("Application shut down successfully")


@limiter.exempt
@app.get("/healthz")
async def healthz():
    """Lightweight health check for local dev and probes."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", app.version),
        "api_version": API_VERSION,
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
        "version": API_VERSION,
        "status": "operational",
        "documentation": "/v1/docs",
    }

api_v1 = APIRouter(prefix="/v1")


@api_v1.get("/status")
async def get_status():
    """Get platform status."""
    return {
        "status": "healthy",
        "orchestrator_initialized": orchestrator is not None and orchestrator.initialized,
        "agents_loaded": orchestrator.get_agent_count() if orchestrator else 0,
    }


# Include routers
api_v1.include_router(agents.router, tags=["agents"])
api_v1.include_router(health.router, tags=["health"])
api_v1.include_router(agent_config.router, tags=["agent-config"])
api_v1.include_router(analytics.router, tags=["analytics"])
api_v1.include_router(connectors.router, tags=["connectors"])
api_v1.include_router(certifications.router, tags=["certifications"])
api_v1.include_router(workflows.router, tags=["workflows"])
api_v1.include_router(audit.router, tags=["audit"])
api_v1.include_router(lineage.router, tags=["lineage"])
api_v1.include_router(documents.router, tags=["documents"])
api_v1.include_router(scope_research.router, tags=["scope-research"])
api_v1.include_router(risk_research.router, tags=["risk-research"])
api_v1.include_router(vendor_research.router, tags=["vendor-research"])
api_v1.include_router(vendor_management.router, tags=["vendor-management"])
api_v1.include_router(compliance_research.router, tags=["compliance-research"])
app.include_router(api_v1)


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
