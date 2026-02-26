"""Runtime path bootstrapper for local execution."""

from __future__ import annotations

import sys
from pathlib import Path


def bootstrap_runtime_paths() -> list[Path]:
    """Ensure repository paths are available for local dev runs."""
    repo_root = Path(__file__).resolve().parents[4]
    _common_src = repo_root / "packages" / "common" / "src"
    if str(_common_src) not in sys.path:
        sys.path.insert(0, str(_common_src))

    from common.bootstrap import ensure_monorepo_paths  # noqa: E402
    ensure_monorepo_paths(repo_root)
    return []
