from routes.analytics import router as analytics_router
from routes.assistant import router as assistant_router
from routes.connectors import router as connectors_router
from routes.documents import router as documents_router
from routes.workflow import router as workflow_router
from routes.workspace import router as workspace_router

FEATURE_ROUTERS = [
    assistant_router,
    workflow_router,
    documents_router,
    analytics_router,
    connectors_router,
    workspace_router,
]
