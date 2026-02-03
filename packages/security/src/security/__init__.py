"""Security utilities for auth and tenant enforcement."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING, Any

from .lineage import mask_lineage_payload
from .secrets import resolve_secret

if TYPE_CHECKING:
    from .auth import AuthContext, AuthTenantMiddleware, authenticate_request
elif importlib.util.find_spec("cryptography") is not None:
    from .auth import AuthContext, AuthTenantMiddleware, authenticate_request
else:

    class AuthContext:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("AuthContext unavailable without cryptography dependency.")

    class AuthTenantMiddleware:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("AuthTenantMiddleware unavailable without cryptography.")

    def authenticate_request(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("authenticate_request unavailable without cryptography.")


__all__ = [
    "AuthContext",
    "AuthTenantMiddleware",
    "authenticate_request",
    "mask_lineage_payload",
    "resolve_secret",
]
