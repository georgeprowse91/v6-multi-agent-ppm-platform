from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_payload(
    *,
    message: str,
    code: str,
    details: Any | None = None,
    correlation_id: str | None = None,
) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {"error": {"message": message, "code": code}}
    if details is not None:
        payload["error"]["details"] = details
    if correlation_id:
        payload["error"]["correlation_id"] = correlation_id
    return payload


def _extract_message(detail: Any) -> tuple[str, Any | None]:
    if isinstance(detail, str):
        return detail, None
    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("error") or "Request failed"
        return message, detail
    return "Request failed", detail


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:  # noqa: ARG001
        message, details = _extract_message(exc.detail)
        correlation_id = getattr(request.state, "correlation_id", None)
        payload = error_payload(
            message=message,
            code=f"http_{exc.status_code}",
            details=details,
            correlation_id=correlation_id,
        )
        headers = dict(exc.headers or {})
        if correlation_id:
            headers.setdefault("X-Correlation-ID", correlation_id)
        return JSONResponse(status_code=exc.status_code, content=payload, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:  # noqa: ARG001
        correlation_id = getattr(request.state, "correlation_id", None)
        payload = error_payload(
            message="Validation error",
            code="validation_error",
            details=exc.errors(),
            correlation_id=correlation_id,
        )
        headers = {"X-Correlation-ID": correlation_id} if correlation_id else None
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload, headers=headers)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:  # noqa: ARG001
        correlation_id = getattr(request.state, "correlation_id", None)
        payload = error_payload(
            message="Internal server error",
            code="internal_error",
            correlation_id=correlation_id,
        )
        headers = {"X-Correlation-ID": correlation_id} if correlation_id else None
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload,
            headers=headers,
        )
