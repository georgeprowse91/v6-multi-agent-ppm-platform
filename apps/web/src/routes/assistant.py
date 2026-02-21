from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from dependencies import get_orchestrator_proxy_client
from web_services.assistant import AssistantService

router = APIRouter(prefix="/v1/api/assistant", tags=["assistant"])


def get_assistant_service() -> AssistantService:
    return AssistantService(get_orchestrator_proxy_client())


@router.post("/send")
async def send_message(
    payload: dict[str, Any],
    service: AssistantService = Depends(get_assistant_service),
) -> dict[str, Any]:
    return await service.send(payload)
