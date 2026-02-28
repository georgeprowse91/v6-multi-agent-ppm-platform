"""Repository-aware path utilities for developer tooling.

This module centralizes how tooling locates repo directories and validates
paths. It is intentionally strict so CLI helpers fail with actionable errors.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

_PRIMARY_ROOT_MARKERS: tuple[str, ...] = (
    ".git",
    "pyproject.toml",
    "package.json",
    "ops/docker/docker-compose.yml",
)
_SECONDARY_ROOT_MARKERS: tuple[str, ...] = ("README.md",)


def _has_marker(path: Path, markers: tuple[str, ...]) -> bool:
    return any((path / marker).exists() for marker in markers)


def find_repo_root(start: Path | None = None) -> Path:
    """Locate the repository root by walking up from a starting path.

    Args:
        start: Optional starting file or directory. Defaults to this file.

    Returns:
        The resolved repository root directory.

    Raises:
        RuntimeError: If no directory containing expected repo markers is found.
    """

    candidate = (start or Path(__file__)).resolve()
    if candidate.is_file():
        candidate = candidate.parent

    for parent in (candidate, *candidate.parents):
        if _has_marker(parent, _PRIMARY_ROOT_MARKERS):
            return parent

    for parent in (candidate, *candidate.parents):
        if _has_marker(parent, _SECONDARY_ROOT_MARKERS):
            return parent

    markers = ", ".join((*_PRIMARY_ROOT_MARKERS, *_SECONDARY_ROOT_MARKERS))
    raise RuntimeError(
        "Unable to locate repository root. Looked for markers: "
        f"{markers}. Start path was {start or Path(__file__)}."
    )


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Return the cached repository root."""

    return find_repo_root()


def tooling_dir() -> Path:
    """Return the tools/ directory."""

    return safe_join(repo_root(), "tools", require_exists=True, should_be_dir=True)


def apps_dir() -> Path:
    """Return the apps/ directory."""

    return safe_join(repo_root(), "apps", require_exists=True, should_be_dir=True)


def integrations_dir() -> Path:
    """Return the integrations/ directory."""

    return safe_join(repo_root(), "integrations", require_exists=True, should_be_dir=True)


def integrations_services_dir() -> Path:
    """Return the integrations/services/ directory."""

    return safe_join(integrations_dir(), "services", require_exists=True, should_be_dir=True)


def services_dir() -> Path:
    """Return the services/ directory."""

    return safe_join(repo_root(), "services", require_exists=True, should_be_dir=True)


def agents_dir() -> Path:
    """Return the agents/ directory."""

    return safe_join(repo_root(), "agents", require_exists=True, should_be_dir=True)


def connectors_dir() -> Path:
    """Return the connectors/ directory."""

    return safe_join(
        repo_root(), "connectors", require_exists=True, should_be_dir=True
    )


def packages_dir() -> Path:
    """Return the packages/ directory."""

    return safe_join(repo_root(), "packages", require_exists=True, should_be_dir=True)


def _iter_existing_src_dirs(base: Path, pattern: str) -> list[Path]:
    """Return existing ``src`` directories under ``base`` for a glob pattern."""

    if not base.exists():
        return []
    return [path for path in base.glob(pattern) if path.is_dir()]


def safe_join(
    base: Path,
    *parts: str,
    require_exists: bool = False,
    should_be_dir: bool | None = None,
) -> Path:
    """Safely join a base path with children and validate the result.

    Args:
        base: The base directory to join against.
        parts: Additional path segments.
        require_exists: When True, the path must exist.
        should_be_dir: When True or False, enforce directory/file type.

    Returns:
        A resolved Path object.

    Raises:
        ValueError: If the joined path escapes the base directory.
        FileNotFoundError: If require_exists is True and the path is missing.
        NotADirectoryError: If should_be_dir is True and the path is not a directory.
        IsADirectoryError: If should_be_dir is False and the path is a directory.
    """

    base_resolved = base.resolve()
    joined = base_resolved.joinpath(*parts).resolve()

    if joined != base_resolved and base_resolved not in joined.parents:
        raise ValueError(f"Resolved path {joined} escapes base directory {base_resolved}.")

    if require_exists and not joined.exists():
        raise FileNotFoundError(f"Expected path {joined} to exist.")

    if should_be_dir is True and joined.exists() and not joined.is_dir():
        raise NotADirectoryError(f"Expected directory at {joined}.")
    if should_be_dir is False and joined.exists() and joined.is_dir():
        raise IsADirectoryError(f"Expected file at {joined}.")

    return joined


def add_runtime_paths(extra_paths: Iterable[Path] | None = None) -> list[Path]:
    """Return runtime source directories that should be added to sys.path.

    Args:
        extra_paths: Optional iterable of additional paths to include.

    Returns:
        A list of resolved paths that can be added to sys.path.
    """

    root = repo_root()
    apps = apps_dir()
    services = services_dir()
    agents = agents_dir()
    packages = packages_dir()

    candidate_paths: list[Path] = [root]
    for base in (apps, services, agents, packages):
        candidate_paths.extend(_iter_existing_src_dirs(base, "*/src"))

    candidate_paths.extend(_iter_existing_src_dirs(agents, "**/src"))

    runtime_src = agents / "runtime" / "src"
    if runtime_src.exists():
        candidate_paths.append(runtime_src)

    if extra_paths:
        candidate_paths.extend(extra_paths)

    return [path.resolve() for path in candidate_paths]


def bootstrap_runtime_paths() -> list[Path]:
    """Add runtime source directories to sys.path for local execution."""

    import sys

    added: list[Path] = []
    for path in add_runtime_paths():
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
            added.append(path)
    return added
