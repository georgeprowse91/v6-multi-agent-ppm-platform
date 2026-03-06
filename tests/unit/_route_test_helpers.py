"""Shared helpers for unit-testing individual route modules in isolation.

The web app's ``routes/__init__.py`` imports *every* route module eagerly.
When a test uses ``importlib.util.spec_from_file_location`` to load a single
route file (e.g. ``briefings.py``), the first ``from routes.X import ...``
triggers that ``__init__.py``, which cascades into importing *all* route
dependencies — many of which are unavailable in a minimal test environment.

This module provides ``stub_routes_package()`` which pre-registers lightweight
stubs for ``routes``, ``routes._deps``, and ``routes._llm_helpers`` so the
target route module can be loaded without triggering the full package init.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import types
from pathlib import Path

_WEB_ROUTES = Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "routes"


def stub_routes_package() -> None:
    """Register stub modules for ``routes``, ``routes._deps``, ``routes._llm_helpers``.

    Safe to call multiple times — only installs stubs that are not yet registered.
    """

    # --- routes package stub ---
    if "routes" not in sys.modules or not hasattr(sys.modules["routes"], "__path__"):
        pkg = types.ModuleType("routes")
        pkg.__path__ = [str(_WEB_ROUTES)]
        pkg.__package__ = "routes"
        sys.modules["routes"] = pkg

    # --- routes._deps stub ---
    if "routes._deps" not in sys.modules:
        # Load the real _deps module by file path (avoids triggering __init__)
        deps_path = _WEB_ROUTES / "_deps.py"
        spec = importlib.util.spec_from_file_location("routes._deps", deps_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["routes._deps"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            # If loading real _deps fails (missing transitive deps), use minimal stub
            stub = types.ModuleType("routes._deps")
            stub.logger = logging.getLogger("routes._deps.stub")
            stub._load_projects = lambda: []
            sys.modules["routes._deps"] = stub

    # --- routes._llm_helpers stub ---
    if "routes._llm_helpers" not in sys.modules:
        llm_path = _WEB_ROUTES / "_llm_helpers.py"
        spec = importlib.util.spec_from_file_location("routes._llm_helpers", llm_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["routes._llm_helpers"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            # Fallback: noop stubs
            import asyncio

            stub = types.ModuleType("routes._llm_helpers")

            async def _noop(*a, **kw):
                return None

            async def _noop_str(*a, **kw):
                return ""

            stub.llm_complete = _noop_str
            stub.llm_complete_json = _noop
            stub.llm_complete_structured = _noop
            sys.modules["routes._llm_helpers"] = stub


def load_route_module(filename: str, module_name: str | None = None):
    """Load a single route module by filename (e.g. ``'briefings.py'``).

    Calls ``stub_routes_package()`` first, then loads and returns the module.
    """
    stub_routes_package()
    mod_name = module_name or filename.replace(".py", "")
    mod_path = _WEB_ROUTES / filename
    spec = importlib.util.spec_from_file_location(mod_name, mod_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod
