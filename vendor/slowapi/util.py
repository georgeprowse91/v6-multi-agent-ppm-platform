"""Minimal slowapi util stub."""
from __future__ import annotations

from starlette.requests import Request


def get_remote_address(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"
