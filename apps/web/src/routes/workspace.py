from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_workspace_state_store
from web_services.workspace import WorkspaceService

router = APIRouter(prefix="/v1/api/workspace", tags=["workspace"])


def get_workspace_service() -> WorkspaceService:
    return WorkspaceService(get_workspace_state_store())


@router.get("/{project_id}")
async def get_workspace_state(
    project_id: str,
    service: WorkspaceService = Depends(get_workspace_service),
):
    return service.get_state(project_id)
