"""
Multi-Agent PPM Platform - FastAPI Application

This is the main entry point for the PPM platform REST API.
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tools.runtime_paths import bootstrap_runtime_paths

bootstrap_runtime_paths()

from api.routes import agents, health
from orchestrator import AgentOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Multi-Agent PPM Platform",
    description="AI-native Project Portfolio Management platform with 25 specialized agents",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
allowed_origins_env = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8501,http://localhost:8000"
)
allowed_origins = (
    ["*"]
    if allowed_origins_env.strip() == "*"
    else [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator = None


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    global orchestrator
    logger.info("Starting Multi-Agent PPM Platform...")

    # Initialize orchestrator
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


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Multi-Agent PPM Platform API",
        "version": "0.1.0",
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
