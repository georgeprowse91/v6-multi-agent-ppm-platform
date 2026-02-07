#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def _parse_api_version(version_path: Path) -> tuple[int, int, int]:
    content = version_path.read_text(encoding="utf-8")
    match = re.search(r"API_VERSION\s*=\s*\"(\d+)\.(\d+)\.(\d+)\"", content)
    if not match:
        raise ValueError("API_VERSION not found in packages/version.py")
    return tuple(int(part) for part in match.groups())


def _extract_unreleased_section(changelog: str) -> str:
    unreleased_match = re.search(r"^## \[Unreleased\]\s*$", changelog, flags=re.MULTILINE)
    if not unreleased_match:
        return ""
    start = unreleased_match.end()
    next_release = re.search(r"^## \[[0-9]+\.[0-9]+\.[0-9]+\]", changelog[start:], flags=re.MULTILINE)
    end = start + next_release.start() if next_release else len(changelog)
    return changelog[start:end]


def _latest_release_version(changelog: str) -> tuple[int, int, int] | None:
    match = re.search(r"^## \[(\d+)\.(\d+)\.(\d+)\]", changelog, flags=re.MULTILINE)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    version_path = repo_root / "packages" / "version.py"
    changelog_path = repo_root / "CHANGELOG.md"

    api_version = _parse_api_version(version_path)
    changelog = changelog_path.read_text(encoding="utf-8")
    unreleased = _extract_unreleased_section(changelog)

    has_breaking = bool(
        re.search(r"^###\s+Breaking\b", unreleased, flags=re.MULTILINE)
        or re.search(r"BREAKING CHANGE", unreleased, flags=re.IGNORECASE)
    )

    latest_release = _latest_release_version(changelog)
    if not latest_release:
        print("No released versions found in CHANGELOG.md; skipping breaking-change check.")
        return

    if has_breaking and api_version[0] <= latest_release[0]:
        raise SystemExit(
            "Breaking changes detected in CHANGELOG.md but API_VERSION major was not bumped. "
            f"Latest release major: {latest_release[0]}, current API_VERSION: {api_version[0]}."
        )

    print("API versioning check passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Versioning check failed: {exc}")
        sys.exit(1)
