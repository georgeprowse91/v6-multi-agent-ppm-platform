"""
Centralized monorepo path bootstrap.

Replaces per-file sys.path.insert() calls with a single, idempotent function
that discovers all source trees. Mirrors the logic in tests/conftest.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BOOTSTRAPPED = False


def ensure_monorepo_paths(repo_root: Path | None = None) -> None:
    """Register all monorepo source trees on sys.path (idempotent).

    Call this once at the top of any service/agent/app entry point instead
    of manually inserting individual paths via ``sys.path.insert()``.

    When *repo_root* is ``None`` the function walks up from this file to
    find the first directory containing ``pyproject.toml``.
    """
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    root = repo_root or _find_repo_root()

    # vendor/stubs must be first so shims shadow any installed packages
    ordered: list[Path] = [root / "vendor" / "stubs", root / "vendor", root]

    src_dirs: list[Path] = []
    for base in (
        "agents",
        "packages",
        "connectors",
        "integrations/services",
        "apps",
        "services",
    ):
        base_path = root / base
        if base_path.exists():
            src_dirs.extend(p for p in base_path.glob("*/src") if p.is_dir())

    # Deep-scan agents (nested directories like agents/core-orchestration/intent-router-agent/src)
    agents_path = root / "agents"
    if agents_path.exists():
        src_dirs.extend(p for p in agents_path.glob("**/src") if p.is_dir())

    runtime_src = agents_path / "runtime" / "src"
    if runtime_src.exists() and runtime_src not in src_dirs:
        src_dirs.append(runtime_src)

    # Prioritise api-gateway/src so its ``api`` package wins over
    # packages/contracts/src/api which would otherwise shadow it.
    api_gw = root / "apps" / "api-gateway" / "src"
    prioritized: list[Path] = []
    if api_gw.exists():
        prioritized.append(api_gw)
    prioritized.extend(p for p in src_dirs if p != api_gw)

    ordered.extend(prioritized)

    seen = set(sys.path)
    new_paths: list[str] = []
    for p in ordered:
        s = str(p.resolve())
        if s not in seen:
            seen.add(s)
            new_paths.append(s)

    sys.path[:0] = new_paths
    _BOOTSTRAPPED = True


def _find_repo_root() -> Path:
    """Walk up from this file to locate the repository root."""
    p = Path(__file__).resolve()
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("Cannot find repo root (no pyproject.toml found)")
