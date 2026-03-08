from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.responses import JSONResponse

try:  # pragma: no cover - exercised in runtime environments with slowapi installed
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address
except ModuleNotFoundError:  # pragma: no cover - fallback used in restricted local envs

    class RateLimitExceeded(Exception):  # noqa: N818
        """Fallback exception type when slowapi is unavailable."""

    class Limiter:
        def __init__(self, key_func: Callable[..., str] | None = None, **_kwargs: Any) -> None:
            self.key_func = key_func

        def limit(self, _rule: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return decorator

        def exempt(self, func: Callable[..., Any]) -> Callable[..., Any]:
            return func

    class SlowAPIMiddleware:
        def __init__(self, app: Callable[..., Any], **_kwargs: Any) -> None:
            self.app = app

        async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
            await self.app(scope, receive, send)

    def get_remote_address(request: Any) -> str:
        client = getattr(request, "client", None)
        return getattr(client, "host", None) or "127.0.0.1"

    async def _rate_limit_exceeded_handler(request: Any, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc) or "Rate limit exceeded"})
