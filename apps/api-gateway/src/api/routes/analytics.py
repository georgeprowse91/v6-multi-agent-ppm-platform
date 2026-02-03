"""
Analytics API Routes

Proxy endpoints for project health analytics.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8080")


def _forward_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key in ("authorization", "x-tenant-id", "x-dev-user"):
        value = request.headers.get(key)
        if value:
            headers[key] = value
    return headers


async def _proxy_request(
    request: Request, method: str, path: str, payload: dict[str, Any] | None = None
) -> Any:
    url = f"{ANALYTICS_SERVICE_URL.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.request(
            method, url, headers=_forward_headers(request), json=payload
        )
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = {"detail": response.text}
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


@router.get("/projects/{project_id}/health")
async def project_health(project_id: str, request: Request) -> Any:
    return await _proxy_request(request, "GET", f"/api/projects/{project_id}/health")


@router.get("/projects/{project_id}/health/trends")
async def project_health_trends(project_id: str, request: Request) -> Any:
    return await _proxy_request(request, "GET", f"/api/projects/{project_id}/health/trends")


@router.post("/projects/{project_id}/health/what-if")
async def project_health_what_if(
    project_id: str, request: Request, payload: dict[str, Any]
) -> Any:
    return await _proxy_request(
        request, "POST", f"/api/projects/{project_id}/health/what-if", payload
    )
