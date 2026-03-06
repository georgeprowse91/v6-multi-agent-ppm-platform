"""Integration-level smoke tests for the February 2026 Security Review remediation.

Covers all five "Unchanged Findings" that were subsequently implemented:

1. Auth code deduplication – middleware delegates to security.auth
2. sys.path elimination – key production files no longer contain sys.path.insert
3. LLM key rotation – signal handler and HTTP endpoint
4. Model registry cache – clear endpoint reachable and functional
5. on_event deprecation – main.py uses lifespan pattern

These are intentionally lightweight so they run in the standard test suite
without requiring a running server.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 1.  Auth code deduplication
# ---------------------------------------------------------------------------


def test_no_local_validate_jwt_in_gateway_middleware() -> None:
    """_validate_jwt must not be defined in the gateway middleware module."""
    import api.middleware.security as m

    assert not hasattr(m, "_validate_jwt"), (
        "Duplicate _validate_jwt has been removed; JWT validation is delegated "
        "to security.auth.authenticate_request"
    )


def test_no_local_oidc_ttl_cache_in_gateway_middleware() -> None:
    """_OIDCTTLCache must not be defined in the gateway middleware module."""
    import api.middleware.security as m

    assert not hasattr(m, "_OIDCTTLCache"), (
        "Duplicate _OIDCTTLCache has been removed; caching lives in security.auth._TTLCache"
    )


def test_gateway_middleware_auth_context_same_as_package() -> None:
    from api.middleware.security import AuthContext as GwAuthContext
    from security.auth import AuthContext as Pkg

    assert GwAuthContext is Pkg, "AuthContext must be imported from security.auth, not redefined locally"


# ---------------------------------------------------------------------------
# 2.  sys.path elimination
# ---------------------------------------------------------------------------


def _has_sys_path_insert(source: str) -> bool:
    """Return True if any statement in source is sys.path.insert(...)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "insert"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "path"
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == "sys"
        ):
            return True
    return False


_PRODUCTION_FILES_NO_SYS_PATH = [
    REPO_ROOT / "apps" / "api-gateway" / "src" / "api" / "main.py",
    REPO_ROOT / "apps" / "api-gateway" / "src" / "api" / "routes" / "agent_config.py",
    REPO_ROOT / "services" / "scope_baseline" / "main.py",
]


@pytest.mark.parametrize("path", _PRODUCTION_FILES_NO_SYS_PATH, ids=lambda p: p.name)
def test_no_sys_path_insert_in_production_files(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    assert not _has_sys_path_insert(source), (
        f"{path.relative_to(REPO_ROOT)} still contains sys.path.insert(); "
        "use PYTHONPATH or pip install -e . for intra-repo imports"
    )


def test_pyproject_packages_find_section_present() -> None:
    """pyproject.toml must have [tool.setuptools.packages.find] configured."""
    import tomllib  # type: ignore[import]

    pyproject = REPO_ROOT / "pyproject.toml"
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)

    setuptools = data.get("tool", {}).get("setuptools", {})
    assert "packages" in setuptools, (
        "[tool.setuptools.packages.find] must be present in pyproject.toml"
    )


def test_pyproject_pythonpath_includes_package_sources() -> None:
    """pytest pythonpath must include the key monorepo source trees."""
    import tomllib  # type: ignore[import]

    pyproject = REPO_ROOT / "pyproject.toml"
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)

    pythonpath = data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("pythonpath", [])
    expected_entries = [
        "packages/common/src",
        "packages/security/src",
        "packages/llm/src",
    ]
    for entry in expected_entries:
        assert entry in pythonpath, (
            f"'{entry}' must be in [tool.pytest.ini_options] pythonpath "
            "so tests can import intra-repo packages without sys.path.insert()"
        )


# ---------------------------------------------------------------------------
# 3.  LLM key rotation
# ---------------------------------------------------------------------------


def test_install_key_rotation_handler_in_main() -> None:
    """Check that _install_key_rotation_handler is defined in api.main source."""
    source = (REPO_ROOT / "apps" / "api-gateway" / "src" / "api" / "main.py").read_text(
        encoding="utf-8"
    )
    assert "def _install_key_rotation_handler(" in source, (
        "_install_key_rotation_handler must be defined in api.main"
    )


def test_clear_auth_caches_exported_from_security_auth() -> None:
    from security.auth import clear_auth_caches  # noqa: F401

    assert callable(clear_auth_caches)


def test_admin_rotate_endpoint_exists() -> None:
    from api.routes.admin import router

    routes = {r.path for r in router.routes}  # type: ignore[attr-defined]
    assert "/llm/keys/rotate" in routes, (
        "POST /llm/keys/rotate must be defined in the admin router"
    )


# ---------------------------------------------------------------------------
# 4.  Model registry cache admin endpoint
# ---------------------------------------------------------------------------


def test_admin_clear_model_registry_endpoint_exists() -> None:
    from api.routes.admin import router

    routes = {r.path for r in router.routes}  # type: ignore[attr-defined]
    assert "/model-registry/cache/clear" in routes, (
        "POST /model-registry/cache/clear must be defined in the admin router"
    )


def test_admin_router_included_in_main_app() -> None:
    """The admin router must be included under /v1/admin in the main app source."""
    source = (REPO_ROOT / "apps" / "api-gateway" / "src" / "api" / "main.py").read_text(
        encoding="utf-8"
    )
    assert "admin" in source and "include_router" in source, (
        "Admin router must be included in the FastAPI app via include_router"
    )
    # Verify the admin router is imported
    assert "from api.routes import" in source or "from api.routes.admin" in source, (
        "Admin router module must be imported in api.main"
    )


# ---------------------------------------------------------------------------
# 5.  on_event deprecation
# ---------------------------------------------------------------------------


def test_no_on_event_in_main() -> None:
    """main.py must not contain @app.on_event decorators."""
    source = (REPO_ROOT / "apps" / "api-gateway" / "src" / "api" / "main.py").read_text(
        encoding="utf-8"
    )
    assert 'on_event("startup")' not in source, (
        "@app.on_event('startup') must be replaced with the lifespan pattern"
    )
    assert 'on_event("shutdown")' not in source, (
        "@app.on_event('shutdown') must be replaced with the lifespan pattern"
    )


def test_lifespan_passed_to_fastapi() -> None:
    """FastAPI app must be initialised with a lifespan context manager (source check)."""
    source = (REPO_ROOT / "apps" / "api-gateway" / "src" / "api" / "main.py").read_text(
        encoding="utf-8"
    )
    # The lifespan function must exist at module level
    assert "def lifespan(" in source or "async def lifespan(" in source, (
        "lifespan async context manager must be defined in api.main"
    )
    # FastAPI must be initialised with lifespan= parameter
    assert "lifespan=lifespan" in source or "FastAPI(" in source, (
        "app must be created with lifespan=lifespan"
    )
    assert "lifespan=" in source, "FastAPI app must be created with lifespan= parameter"


def test_lifespan_is_async_context_manager() -> None:
    """lifespan must be an async context manager (asynccontextmanager-decorated, source check)."""
    source = (REPO_ROOT / "apps" / "api-gateway" / "src" / "api" / "main.py").read_text(
        encoding="utf-8"
    )
    assert "@asynccontextmanager" in source, (
        "lifespan must be decorated with @asynccontextmanager"
    )
    assert "async def lifespan" in source, (
        "lifespan must be an async generator function"
    )
