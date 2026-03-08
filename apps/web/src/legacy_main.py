"""PPM Web Console — entry-point module.

This file used to contain ~7,600 lines and ~294 functions.  All route
handlers have been extracted into ``routes/`` sub-modules.  This file
now serves **only** as the application assembly point:

1. ``sys.path`` bootstrap
2. FastAPI app creation + middleware
3. Observability (metrics, tracing)
4. Static file mounts
5. Startup lifecycle (demo seed, knowledge store)
6. Router registration

Route modules live under ``apps/web/src/routes/``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

# ---------------------------------------------------------------------------
# Monorepo path bootstrap
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[3]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

# ---------------------------------------------------------------------------
# First-party imports that depend on the monorepo path
# ---------------------------------------------------------------------------
from demo_seed import seed_demo_data  # noqa: E402
from knowledge_store import KnowledgeStore  # noqa: E402
from methodology_node_runtime import load_methodology_node_runtime_registry  # noqa: E402
from observability.metrics import configure_metrics  # noqa: E402

# ---------------------------------------------------------------------------
# Route module registry
# ---------------------------------------------------------------------------
from routes import LEGACY_ROUTE_MODULES  # noqa: E402

# ---------------------------------------------------------------------------
# Shared state and helpers (used by all route modules via routes._deps)
# ---------------------------------------------------------------------------
from routes._deps import (  # noqa: E402
    FRONTEND_DIST_DIR,
    KNOWLEDGE_DB_PATH,
    SESSION_COOKIE,
    STATIC_DIR,
    _cookie_secure,
    _demo_mode_enabled,
    _demo_session_payload,
    _encode_cookie,
    _permissions_for_user,
    _session_from_request,
    demo_outbox,
    spreadsheet_store,
    timeline_store,
    tree_store,
    workspace_state_store,
)
from security.api_governance import apply_api_governance  # noqa: E402
from template_mappings import load_template_mappings  # noqa: E402

from config import validate_startup_config  # noqa: E402
from packages.version import API_VERSION  # noqa: E402

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(title="PPM Web Console", version=API_VERSION)
api_router = APIRouter(prefix="/v1")

# Static file mounts
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if FRONTEND_DIST_DIR.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")

apply_api_governance(app, service_name="web")

# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------
_meter = configure_metrics("web-ui")
post_login_landing_success_total = _meter.create_counter(
    name="post_login_landing_success_total",
    description="Total successful post-login landing redirects.",
    unit="1",
)

# Expose the counter to the auth route module so it can record metrics.
import routes._deps as _deps_module  # noqa: E402

_deps_module.post_login_landing_success_total = post_login_landing_success_total  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------
validate_startup_config()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class PermissionMiddleware(BaseHTTPMiddleware):
    """Enforce ``@permission_required(...)`` decorators on route handlers."""

    async def dispatch(self, request: Request, call_next):
        endpoint = request.scope.get("endpoint")
        required = getattr(endpoint, "required_permissions", None)
        if required:
            session = _session_from_request(request)
            if not session:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
            permissions = _permissions_for_user(request, session)
            if not permissions.intersection(required):
                return JSONResponse(status_code=403, content={"detail": "Permission denied"})
        return await call_next(request)


class DemoAutoSessionMiddleware(BaseHTTPMiddleware):
    """Auto-create a demo session for first-time visitors in demo mode."""

    async def dispatch(self, request: Request, call_next):
        if not _demo_mode_enabled():
            return await call_next(request)
        if request.url.path not in {"/", "/app"}:
            return await call_next(request)
        if _session_from_request(request):
            return await call_next(request)
        response = RedirectResponse(url="/app?project_id=demo-predictive", status_code=307)
        response.set_cookie(
            SESSION_COOKIE,
            _encode_cookie(_demo_session_payload(), 8 * 60 * 60),
            httponly=True,
            secure=_cookie_secure(),
            samesite="lax",
        )
        return response


app.add_middleware(PermissionMiddleware)
app.add_middleware(DemoAutoSessionMiddleware)


# ---------------------------------------------------------------------------
# Startup lifecycle
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup() -> None:
    import routes._deps as deps

    deps.knowledge_store = KnowledgeStore(KNOWLEDGE_DB_PATH)
    load_template_mappings()
    load_methodology_node_runtime_registry()
    if _demo_mode_enabled():
        seed_demo_data(
            workspace_state_store=workspace_state_store,
            spreadsheet_store=spreadsheet_store,
            timeline_store=timeline_store,
            tree_store=tree_store,
            knowledge_db_path=KNOWLEDGE_DB_PATH,
            demo_outbox=demo_outbox,
        )


# ---------------------------------------------------------------------------
# Register all extracted route modules on the v1 API router
# ---------------------------------------------------------------------------
for _router in LEGACY_ROUTE_MODULES:
    api_router.include_router(_router)


# ---------------------------------------------------------------------------
# Root-level catch-all routes (outside /v1 prefix)
# ---------------------------------------------------------------------------


@api_router.get("/")
async def index() -> FileResponse:
    if FRONTEND_DIST_DIR.exists():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
    return FileResponse(STATIC_DIR / "index.html")


@api_router.get("/app")
async def v1_app_entrypoint() -> RedirectResponse:
    return RedirectResponse(url="/app", status_code=307)


# ---------------------------------------------------------------------------
# Final assembly
# ---------------------------------------------------------------------------
app.include_router(api_router)


# ---------------------------------------------------------------------------
# Dev server
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8501, reload=False)
