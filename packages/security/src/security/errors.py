from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_payload(
    *, message: str, code: str, details: Any | None = None
) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {"error": {"message": message, "code": code}}
    if details is not None:
        payload["error"]["details"] = details
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
        payload = error_payload(message=message, code=f"http_{exc.status_code}", details=details)
        return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:  # noqa: ARG001
        payload = error_payload(
            message="Validation error", code="validation_error", details=exc.errors()
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:  # noqa: ARG001
        payload = error_payload(message="Internal server error", code="internal_error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload,
        )
