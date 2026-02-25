from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

# Content-Security-Policy directive sets. The default policy is strict; an
# optional list of trusted script/style sources can be added via environment
# variable CSP_EXTRA_SCRIPT_SRCS (space-separated) for deployments that need
# to load assets from a CDN or approved third party.
_CSP_BASE_DIRECTIVES: list[str] = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",  # unsafe-inline required for CSS-in-JS design tokens
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    "upgrade-insecure-requests",
]


def _build_csp(extra_script_srcs: str | None = None) -> str:
    directives = list(_CSP_BASE_DIRECTIVES)
    if extra_script_srcs:
        # Append any operator-approved CDN hosts to the script-src directive.
        for idx, directive in enumerate(directives):
            if directive.startswith("script-src "):
                directives[idx] = f"{directive} {extra_script_srcs.strip()}"
                break
    return "; ".join(directives)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        enable_hsts: bool = True,
        csp_extra_script_srcs: str | None = None,
    ) -> None:
        super().__init__(app)
        self._enable_hsts: bool = enable_hsts
        extra = csp_extra_script_srcs or os.getenv("CSP_EXTRA_SCRIPT_SRCS")
        self._csp: str = _build_csp(extra)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", self._csp)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if self._enable_hsts and request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
            )
        return response
