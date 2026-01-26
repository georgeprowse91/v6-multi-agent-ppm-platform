#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def _join(*parts: str) -> str:
    return "".join(parts)


FILLER_PATTERNS = [
    _join("add", r"\s+", "here"),
    _join("what", r"\s+", "to", r"\s+", "add", r"\s+", "here"),
    _join("what", r"\s+", "belongs", r"\s+", "here"),
    _join("to", r"\s+", "be", r"\s+", "added"),
    _join("coming", r"\s+", "soon"),
    _join("t", "b", "d"),
    _join("to", "do"),
    _join("place", "holder"),
    _join("lorem", r"\s+", "ipsum"),
    _join("<", "insert"),
    _join("<", "to", "do"),
    _join("fill", r"\s+", "this"),
    _join("fix", "me"),
]

ALLOWED_TASK_MARKER = re.compile(
    r"\b(?:" + _join("TO", "DO") + r"|" + _join("FI", "XME") + r")\(#\d+\):"
)
ALLOWED_CONTEXT_PATTERNS = [
    re.compile(r"\bcheck-placeholders(?:\.py)?\b", re.IGNORECASE),
]

TEXT_EXTENSIONS = {
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".graphql",
    ".gql",
}

IGNORED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.name == "check-placeholders.py":
            continue
        if path.is_file() and _is_text_file(path):
            yield path


def _scan_file(
    path: Path, pattern: re.Pattern[str], allowlist: list[re.Pattern[str]] | None = None
) -> list[tuple[int, str]]:
    matches = []
    lines = path.read_text(errors="ignore").splitlines()
    for idx, line in enumerate(lines, start=1):
        if pattern.search(line):
            if path.name.endswith(".schema.json") and '"enum"' in line:
                continue
            if allowlist and any(allowed.search(line) for allowed in allowlist):
                continue
            matches.append((idx, line.strip()))
    return matches


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    violations: list[str] = []

    filler_regex = re.compile("|".join(FILLER_PATTERNS), re.IGNORECASE)
    task_marker_regex = re.compile(
        r"\b(?:" + _join("TO", "DO") + r"|" + _join("FI", "XME") + r")\b"
    )

    for path in _iter_files(root):
        filler_hits = _scan_file(path, filler_regex, ALLOWED_CONTEXT_PATTERNS)
        for line_no, line in filler_hits:
            violations.append(f"{path}:{line_no}: forbidden phrase found: {line}")

        task_marker_hits = _scan_file(path, task_marker_regex)
        for line_no, line in task_marker_hits:
            if ALLOWED_TASK_MARKER.search(line):
                continue
            violations.append(
                f"{path}:{line_no}: task markers must include issue reference: {line}"
            )

    if violations:
        print("Forbidden phrase scan failed:")
        for violation in violations:
            print(f"  - {violation}")
        return 1

    print("Forbidden phrase scan passed with no matches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
