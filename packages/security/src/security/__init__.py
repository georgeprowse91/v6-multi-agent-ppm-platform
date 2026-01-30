"""Security utilities for auth and tenant enforcement."""

from __future__ import annotations

import importlib.util

from .lineage import mask_lineage_payload
from .secrets import resolve_secret


if importlib.util.find_spec("cryptography") is not None:
    from .auth import AuthContext, AuthTenantMiddleware, authenticate_request
else:
    class AuthContext:  # type: ignore[override]
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("AuthContext unavailable without cryptography dependency.")

    class AuthTenantMiddleware:  # type: ignore[override]
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("AuthTenantMiddleware unavailable without cryptography.")

    def authenticate_request(*args, **kwargs):  # type: ignore[override]
        raise RuntimeError("authenticate_request unavailable without cryptography.")

__all__ = [
    "AuthContext",
    "AuthTenantMiddleware",
    "authenticate_request",
    "mask_lineage_payload",
    "resolve_secret",
]
