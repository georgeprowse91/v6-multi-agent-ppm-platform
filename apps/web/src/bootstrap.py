from __future__ import annotations

from fastapi import FastAPI
from legacy_main import app as legacy_app
from middleware import configure_application_middleware
from routes import FEATURE_ROUTERS


def create_app() -> FastAPI:
    app = legacy_app
    configure_application_middleware(app)
    for router in FEATURE_ROUTERS:
        app.include_router(router)
    return app
