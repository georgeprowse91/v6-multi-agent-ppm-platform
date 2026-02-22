from __future__ import annotations

from typing import Any

from dependencies import get_data_service_client
from fastapi import APIRouter, Depends
from web_services.workflow import WorkflowService

router = APIRouter(prefix="/v1/api/workflows", tags=["workflow"])


def get_workflow_service() -> WorkflowService:
    return WorkflowService(get_data_service_client())


@router.post("/start")
async def start_workflow(
    payload: dict[str, Any],
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return await service.start_workflow(payload)
