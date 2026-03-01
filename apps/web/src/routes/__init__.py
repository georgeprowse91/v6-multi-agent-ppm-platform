"""Route registry — collects all decomposed route modules.

The pre-existing v1 stub routers are kept alongside the new
legacy_main.py route modules for backwards compatibility.
"""
from __future__ import annotations

# Pre-existing v1 stub routers (thin service-layer wrappers)
from routes.analytics import router as analytics_router
from routes.assistant import router as assistant_stub_router
from routes.connectors import legacy_router as connectors_legacy_router
from routes.connectors import router as connectors_stub_router
from routes.documents import router as documents_stub_router
from routes.workflow import router as workflow_stub_router
from routes.workspace import router as workspace_stub_router

# New route modules extracted from legacy_main.py
from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.roles import router as roles_router
from routes.methodology import router as methodology_router
from routes.intake import router as intake_router
from routes.workspace_state import router as workspace_state_router
from routes.agents import router as agents_router
from routes.assistant_api import router as assistant_api_router
from routes.llm import router as llm_router
from routes.tree import router as tree_router
from routes.timeline import router as timeline_router
from routes.wbs_schedule import router as wbs_schedule_router
from routes.spreadsheets import router as spreadsheets_router
from routes.templates_api import router as templates_api_router
from routes.knowledge import router as knowledge_router
from routes.search import router as search_router
from routes.dashboards import router as dashboards_router
# connectors_api.py has been consolidated into connectors.py (legacy_router)
from routes.document_canvas import router as document_canvas_router
from routes.pipeline import router as pipeline_router
from routes.workflows_api import router as workflows_api_router
from routes.enterprise import router as enterprise_router
from routes.legacy_pages import router as legacy_pages_router
from routes.agent_runs import router as agent_runs_router

# Pre-existing v1 stubs (mounted with their own prefix in their own files)
FEATURE_ROUTERS = [
    assistant_stub_router,
    workflow_stub_router,
    documents_stub_router,
    analytics_router,
    connectors_stub_router,
    workspace_stub_router,
]

# All route modules extracted from legacy_main.py (no prefix — they define full paths)
LEGACY_ROUTE_MODULES = [
    health_router,
    auth_router,
    roles_router,
    methodology_router,
    intake_router,
    workspace_state_router,
    agents_router,
    assistant_api_router,
    llm_router,
    tree_router,
    timeline_router,
    wbs_schedule_router,
    spreadsheets_router,
    templates_api_router,
    knowledge_router,
    search_router,
    dashboards_router,
    connectors_legacy_router,
    document_canvas_router,
    pipeline_router,
    workflows_api_router,
    enterprise_router,
    legacy_pages_router,
    agent_runs_router,
]
