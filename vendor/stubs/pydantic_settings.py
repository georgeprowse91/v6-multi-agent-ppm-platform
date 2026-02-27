"""Minimal pydantic_settings compatibility shim.

When real pydantic-settings is installed, this module transparently re-exports
the real implementation.  In offline environments it provides a bare-bones
fallback.
"""
from __future__ import annotations

import importlib
import os
import sys
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_real_pydantic_settings() -> bool:
    """Try to load the real pydantic_settings, bypassing this stub."""
    def _is_stub_provider(p: str) -> bool:
        return os.path.abspath(os.path.join(p, "pydantic_settings.py")) == os.path.abspath(__file__)

    has_real = False
    for search_path in sys.path:
        if not search_path or _is_stub_provider(search_path):
            continue
        # Check for real package (directory with __init__.py)
        candidate = os.path.join(search_path, "pydantic_settings", "__init__.py")
        if os.path.isfile(candidate):
            has_real = True
            break
    if not has_real:
        return False

    saved_path = sys.path[:]
    saved_mod = sys.modules.pop("pydantic_settings", None)
    sys.path = [p for p in sys.path if not _is_stub_provider(p)]

    try:
        _real = importlib.import_module("pydantic_settings")
        sys.modules["pydantic_settings"] = _real
        our_globals = globals()
        for attr in dir(_real):
            if not attr.startswith("__"):
                our_globals[attr] = getattr(_real, attr)
        return True
    except Exception:
        if saved_mod is not None:
            sys.modules["pydantic_settings"] = saved_mod
        return False
    finally:
        sys.path = saved_path


_USING_REAL = _load_real_pydantic_settings()

if not _USING_REAL:
    class BaseSettings:
        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    class SettingsConfigDict(dict):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
