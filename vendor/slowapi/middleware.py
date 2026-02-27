"""Minimal slowapi middleware with functional rate limiting."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SlowAPIMiddleware(BaseHTTPMiddleware):
    """Rate-limiting middleware that enforces the app's limiter default limits."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Retrieve the limiter from app.state (set as `app.state.limiter` in main.py).
        app = request.scope.get("app")
        limiter = getattr(getattr(app, "state", None), "limiter", None) if app else None
        if limiter is not None and hasattr(limiter, "is_rate_limited"):
            key = limiter._key_func(request)
            if limiter.is_rate_limited(key):
                return Response("Rate limit exceeded", status_code=429)
        return await call_next(request)
