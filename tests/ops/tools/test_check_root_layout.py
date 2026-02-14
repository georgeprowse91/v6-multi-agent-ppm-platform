from __future__ import annotations

from pathlib import Path

from ops.tools.check_root_layout import find_unexpected_root_entries


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


def test_find_unexpected_root_entries_returns_empty_when_allowlisted(tmp_path: Path) -> None:
    _touch(tmp_path / "README.md")
    _touch(tmp_path / "pyproject.toml")
    (tmp_path / "apps").mkdir()

    unexpected = find_unexpected_root_entries(tmp_path)

    assert unexpected == []


def test_find_unexpected_root_entries_flags_new_root_artifacts(tmp_path: Path) -> None:
    _touch(tmp_path / "README.md")
    _touch(tmp_path / "pyproject.toml")
    _touch(tmp_path / "scratch-notes.txt")

    unexpected = find_unexpected_root_entries(tmp_path)

    assert unexpected == ["scratch-notes.txt"]
