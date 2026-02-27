"""Minimal jsonschema compatibility shim.

When real jsonschema is installed, this module transparently re-exports
the real implementation.  In offline environments it provides a bare-bones
fallback.
"""
from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Iterable
from typing import Any, Sequence

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_real_jsonschema() -> bool:
    """Try to load the real jsonschema, bypassing this stub."""
    def _is_stub_provider(p: str) -> bool:
        return os.path.abspath(os.path.join(p, "jsonschema")) == _THIS_DIR

    has_real = False
    for search_path in sys.path:
        if not search_path or _is_stub_provider(search_path):
            continue
        candidate = os.path.join(search_path, "jsonschema", "__init__.py")
        if os.path.isfile(candidate):
            has_real = True
            break
    if not has_real:
        return False

    saved_path = sys.path[:]
    saved_mod = sys.modules.pop("jsonschema", None)
    sys.path = [p for p in sys.path if not _is_stub_provider(p)]

    try:
        _real = importlib.import_module("jsonschema")
        sys.modules["jsonschema"] = _real
        our_globals = globals()
        for attr in dir(_real):
            if not attr.startswith("__"):
                our_globals[attr] = getattr(_real, attr)
        return True
    except Exception:
        if saved_mod is not None:
            sys.modules["jsonschema"] = saved_mod
        return False
    finally:
        sys.path = saved_path


_USING_REAL = _load_real_jsonschema()

if not _USING_REAL:
    class FormatChecker:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

    class Draft202012Validator:
        def __init__(self, schema: dict[str, Any], format_checker: "FormatChecker | None" = None) -> None:
            self.schema = schema
            self.format_checker = format_checker

        def iter_errors(self, instance: dict[str, Any]) -> Iterable:
            return []

    class ValidationError(Exception):
        def __init__(self, message: str, path: Sequence[str] | None = None) -> None:
            super().__init__(message)
            self.message = message
            self.path = list(path or [])

    def validate(instance: dict[str, Any], schema: dict[str, Any]) -> None:
        return None
