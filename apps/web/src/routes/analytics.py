from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from dependencies import get_analytics_client
from web_services.analytics import AnalyticsService

router = APIRouter(prefix="/v1/api/analytics", tags=["analytics"])


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService(get_analytics_client())


@router.get("/powerbi/{report_type}")
async def get_powerbi_report(
    report_type: str,
    project_id: str | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return await service.get_report(report_type=report_type, project_id=project_id)
