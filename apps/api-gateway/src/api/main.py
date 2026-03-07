"""
Multi-Agent PPM Platform - FastAPI Application

This is the main entry point for the PPM platform REST API.
"""

import logging
import os
import signal
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from common.env_validation import environment_value
from common.exceptions import PPMPlatformError, exception_to_http_status
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from observability.logging import configure_logging
from observability.metrics import RequestMetricsMiddleware, configure_metrics
from observability.tracing import TraceMiddleware, configure_tracing
from security.auth import clear_auth_caches
from security.errors import register_error_handlers
from security.headers import SecurityHeadersMiddleware

from api.bootstrap import StartupFailure, build_default_bootstrap_registry
from api.config import validate_startup_config
from api.cors import ALLOWED_CORS_HEADERS, ALLOWED_CORS_METHODS, get_allowed_origins
from api.limiter import limiter
from api.middleware.security import AuthTenantMiddleware, FieldMaskingMiddleware
from api.routes import (
    admin,
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
    marketplace,
    prompts,
    risk_research,
    scope_research,
    vendor_management,
    vendor_research,
    workflows,
)
from api.slowapi_compat import (
    RateLimitExceeded,
    SlowAPIMiddleware,
    _rate_limit_exceeded_handler,
)
from packages.version import API_VERSION

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

validate_startup_config()

environment = environment_value(os.environ)


def _install_key_rotation_handler() -> None:
    """Install SIGUSR1 handler for in-process LLM key and JWKS cache rotation.

    Sending SIGUSR1 to the process clears the cached OIDC discovery document
    and JWKS data in ``security.auth``, forcing fresh resolution on the next
    request.  This provides zero-downtime rotation when IdP keys or LLM API
    keys are rotated in the secret store.
    """
    if not hasattr(signal, "SIGUSR1"):  # pragma: no cover - Windows
        logger.info(
            "key_rotation_handler_skipped",
            extra={"reason": "SIGUSR1 not available on this platform"},
        )
        return

    def _handle_rotation(signum: int, frame: object) -> None:
        clear_auth_caches()
        logger.info("llm_key_rotation_triggered", extra={"signal": "SIGUSR1"})

    signal.signal(signal.SIGUSR1, _handle_rotation)
    logger.info("llm_key_rotation_handler_installed", extra={"signal": "SIGUSR1"})


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager (replaces deprecated @app.on_event handlers).

    Startup section initialises the bootstrap registry and installs the
    in-process LLM key-rotation signal handler.  Shutdown section tears down
    registered bootstrap components gracefully.
    """
    # --- startup ---
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

    _install_key_rotation_handler()
    logger.info("Application started successfully")

    yield

    # --- shutdown ---
    logger.info("Shutting down Multi-Agent PPM Platform...")
    bootstrap_registry = getattr(app.state, "bootstrap_registry", None)
    if bootstrap_registry:
        await bootstrap_registry.shutdown(app)
    logger.info("Application shut down successfully")


# Module-level orchestrator reference — updated by bootstrap at startup.
# Exposed here so tests can patch it with `patch("api.main.orchestrator", ...)`.
orchestrator: Any | None = None

# Create FastAPI application
app = FastAPI(
    title="Multi-Agent PPM Platform",
    description="AI-native Project Portfolio Management platform with 25 specialized agents",
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


def _version_payload() -> dict[str, str]:
    return {
        "service": "multi-agent-ppm-api",
        "api_version": API_VERSION,
        "version": os.getenv("APP_VERSION", app.version),
        "build_sha": os.getenv("BUILD_SHA", "unknown"),
    }


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
@app.get("/api/health")
async def api_health() -> dict[str, Any]:
    """Health check endpoint accessible under the /api prefix."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
api_v1.include_router(marketplace.router, tags=["marketplace"])
api_v1.include_router(admin.router, prefix="/admin", tags=["admin"])
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
        str(exc)
        if environment in {"dev", "development", "local", "test"}
        else "Internal server error"
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
