from __future__ import annotations

from analytics_proxy import AnalyticsServiceClient


class AnalyticsService:
    def __init__(self, analytics_client: AnalyticsServiceClient) -> None:
        self._analytics_client = analytics_client

    async def get_report(self, report_type: str, project_id: str | None) -> dict:
        response = await self._analytics_client.get_powerbi_report(
            report_type=report_type,
            headers={"X-Project-ID": project_id} if project_id else {},
        )
        return response.json()
