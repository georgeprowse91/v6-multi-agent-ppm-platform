"""
Multi-Agent PPM Platform - FastAPI Application

This is the main entry point for the PPM platform REST API.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.cors import ALLOWED_CORS_HEADERS, ALLOWED_CORS_METHODS, get_allowed_origins
from api.bootstrap import StartupFailure, build_default_bootstrap_registry
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
    prompts,
    risk_research,
    scope_research,
    vendor_management,
    vendor_research,
    workflows,
)
from api.config import validate_startup_config

REPO_ROOT = Path(__file__).resolve().parents[4]
COMMON_ROOT = REPO_ROOT / "packages" / "common" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
for path_root in (REPO_ROOT, COMMON_ROOT, OBSERVABILITY_ROOT, SECURITY_ROOT):
    if str(path_root) not in sys.path:
        sys.path.insert(0, str(path_root))

from packages.version import API_VERSION  # noqa: E402
from observability.logging import configure_logging  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.errors import register_error_handlers  # noqa: E402
from security.headers import SecurityHeadersMiddleware  # noqa: E402
from common.env_validation import environment_value  # noqa: E402
from common.exceptions import PPMPlatformError, exception_to_http_status  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

validate_startup_config()

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


environment = environment_value(os.environ)

# Configure CORS
allowed_origins = get_allowed_origins(environment)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=ALLOWED_CORS_METHODS,
    allow_headers=ALLOWED_CORS_HEADERS,
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

@app.on_event("startup")
async def startup_event() -> None:
    """Initialize application on startup."""
    logger.info("Starting Multi-Agent PPM Platform...")
    app.state.environment = environment
    app.state.bootstrap_registry = build_default_bootstrap_registry()
    try:
        await app.state.bootstrap_registry.startup(app)
    except StartupFailure as exc:
        logger.error(
            "Application startup failed",
            extra={
                "component": exc.component,
                "error": exc.message,
                "startup_order": exc.startup_order,
            },
        )
        raise RuntimeError(str(exc)) from exc

    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on shutdown."""
    logger.info("Shutting down Multi-Agent PPM Platform...")

    bootstrap_registry = getattr(app.state, "bootstrap_registry", None)
    if bootstrap_registry:
        await bootstrap_registry.shutdown(app)

    logger.info("Application shut down successfully")


@limiter.exempt
@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    """Lightweight health check for local dev and probes."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": os.getenv("APP_VERSION", app.version),
        "api_version": API_VERSION,
    }


@limiter.exempt
@app.get("/version")
async def version() -> dict[str, str]:
    """Return API version metadata."""
    return _version_payload()


@limiter.exempt
@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint - API information."""
    return {
        "name": "Multi-Agent PPM Platform API",
        "version": API_VERSION,
        "status": "operational",
        "documentation": "/v1/docs",
    }

api_v1 = APIRouter(prefix="/v1")


@api_v1.get("/status")
async def get_status() -> dict[str, Any]:
    """Get platform status."""
    orchestrator = getattr(app.state, "orchestrator", None)
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
api_v1.include_router(prompts.router, tags=["prompts"])
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


@app.exception_handler(PPMPlatformError)
async def platform_exception_handler(request: Request, exc: PPMPlatformError) -> JSONResponse:
    """Handle platform-specific exceptions."""
    status_code = exception_to_http_status(exc)
    logger.warning("Platform exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "details": getattr(exc, "details", {}),
        },
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all uncaught exceptions."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    # Only include the exception message in development; production gets a generic message.
    message = (
        str(exc) if environment in {"dev", "development", "local", "test"} else "Internal server error"
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": message,
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
