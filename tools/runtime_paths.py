from __future__ import annotations

import sys
from pathlib import Path


def bootstrap_runtime_paths() -> None:
    """Add runtime source directories to sys.path for local execution."""
    repo_root = Path(__file__).resolve().parents[1]

    candidate_paths = []

    # Apps (e.g., api-gateway, orchestration-service)
    apps_dir = repo_root / "apps"
    if apps_dir.exists():
        for path in apps_dir.glob("*/src"):
            candidate_paths.append(path)

    # Agents (agent implementations)
    agents_dir = repo_root / "agents"
    if agents_dir.exists():
        for path in agents_dir.glob("**/src"):
            candidate_paths.append(path)

    # Runtime helpers
    runtime_src = agents_dir / "runtime" / "src"
    if runtime_src.exists():
        candidate_paths.append(runtime_src)

    for path in candidate_paths:
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
