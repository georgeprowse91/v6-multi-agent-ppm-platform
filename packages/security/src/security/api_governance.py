from __future__ import annotations

import os
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from packages.version import API_VERSION
from security.errors import register_error_handlers
from security.headers import SecurityHeadersMiddleware

API_PREFIX = "/v1"
AUTHORIZATION_HEADER = "Authorization"
TENANT_HEADER = "X-Tenant-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
PAGINATION_HEADERS = ("X-Page", "X-Page-Size", "X-Total-Count", "Link")


@dataclass(slots=True)
class Pagination:
    page: int = 1
    page_size: int = 50
    total_count: int | None = None


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers.setdefault(CORRELATION_ID_HEADER, correlation_id)
        response.headers.setdefault("X-API-Version", API_VERSION)
        return response


def apply_api_governance(app: FastAPI, *, service_name: str) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.state.service_name = service_name
    register_error_handlers(app)


def set_pagination_headers(
    response: Response, *, page: int, page_size: int, total_count: int
) -> None:
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Count"] = str(total_count)


def health_response_payload(
    *, service: str, status: str = "ok", dependencies: dict[str, str] | None = None
) -> dict[str, object]:
    return {
        "status": status,
        "service": service,
        "version": API_VERSION,
        "dependencies": dependencies or {},
    }


def version_response_payload(service: str) -> dict[str, str]:
    return {
        "service": service,
        "version": API_VERSION,
        "api_version": API_VERSION,
        "build_sha": os.getenv("BUILD_SHA", "unknown"),
    }
