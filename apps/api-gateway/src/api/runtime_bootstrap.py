"""Runtime path bootstrapper for local execution."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import cast


def bootstrap_runtime_paths() -> list[Path]:
    """Ensure repository paths are available for local dev runs."""
    repo_root = Path(__file__).resolve().parents[4]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    runtime_module = importlib.import_module("tools.runtime_paths")
    return cast(list[Path], runtime_module.bootstrap_runtime_paths())
