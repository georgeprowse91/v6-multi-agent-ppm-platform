"""Tests for tools.runtime_paths utilities."""

from __future__ import annotations

import pytest

from tools import runtime_paths


def test_repo_root_detects_markers() -> None:
    root = runtime_paths.repo_root()
    assert (root / "pyproject.toml").exists()
    assert (root / "tools").exists()


def test_safe_join_rejects_escape() -> None:
    root = runtime_paths.repo_root()
    with pytest.raises(ValueError):
        runtime_paths.safe_join(root, "..")


def test_apps_dir_exists() -> None:
    apps = runtime_paths.apps_dir()
    assert apps.is_dir()
    assert (apps / "web").exists()
