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
    existing = sys.modules.get("routes")
    web_routes_str = str(_WEB_ROUTES)
    if (
        existing is None
        or not hasattr(existing, "__path__")
        or web_routes_str not in list(existing.__path__)
    ):
        pkg = types.ModuleType("routes")
        pkg.__path__ = [web_routes_str]
        pkg.__package__ = "routes"
        sys.modules["routes"] = pkg
        # Clear stale sub-modules from a different routes package
        for key in list(sys.modules):
            if key.startswith("routes."):
                del sys.modules[key]

    # --- routes._deps stub ---
    if "routes._deps" not in sys.modules:
        # Loading _deps.py requires web/src modules.  Integration tests may
        # have cached incompatible modules (e.g. orchestration-service's
        # orchestrator.py as sys.modules["orchestrator"]).  Temporarily
        # remove conflicting entries, load _deps, then restore them.
        deps_path = _WEB_ROUTES / "_deps.py"
        _web_src = deps_path.parent.parent
        _conflicting = {}
        for mod_name in ("orchestrator", "persistence", "config"):
            cached = sys.modules.get(mod_name)
            if cached is not None:
                origin = getattr(cached, "__file__", "") or ""
                if str(_web_src) not in origin:
                    _conflicting[mod_name] = sys.modules.pop(mod_name)

        spec = importlib.util.spec_from_file_location("routes._deps", deps_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["routes._deps"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            # Fallback: minimal stub with common names
            stub = types.ModuleType("routes._deps")
            stub.__file__ = str(deps_path)
            stub.logger = logging.getLogger("routes._deps.stub")
            stub._load_projects = lambda: []
            # Add commonly imported constants
            stub.REPO_ROOT = _web_src.parent.parent.parent
            stub.WEB_ROOT = _web_src.parent
            stub.DATA_DIR = _web_src.parent / "data"
            stub.STORAGE_DIR = _web_src.parent / "storage"
            stub.PROJECTS_PATH = stub.DATA_DIR / "projects.json"
            sys.modules["routes._deps"] = stub

        # Restore conflicting modules
        for mod_name, cached_mod in _conflicting.items():
            sys.modules[mod_name] = cached_mod

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
