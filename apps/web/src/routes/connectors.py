from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_connector_hub_client
from web_services.connectors import ConnectorService

router = APIRouter(prefix="/v1/api/connector-gallery", tags=["connectors"])


def get_connector_service() -> ConnectorService:
    return ConnectorService(get_connector_hub_client())


@router.get("/instances")
async def list_instances(service: ConnectorService = Depends(get_connector_service)) -> list[dict]:
    return await service.list_instances()
