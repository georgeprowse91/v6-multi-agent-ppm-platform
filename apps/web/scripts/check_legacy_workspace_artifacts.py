#!/usr/bin/env python3
"""Guard against reintroducing legacy workspace artifacts in apps/web."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    id: str
    description: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class AllowRule:
    path: str
    check_id: str
    contains: str


TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".scss",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".sh",
    ".html",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_allowlist(path: Path) -> list[AllowRule]:
    rules: list[AllowRule] = []
    if not path.exists():
        return rules

    for idx, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [part.strip() for part in line.split("|", maxsplit=2)]
        if len(parts) != 3 or not all(parts):
            raise ValueError(
                f"Invalid allowlist entry at {path}:{idx}; expected 'path|check_id|contains'."
            )
        rules.append(AllowRule(path=parts[0], check_id=parts[1], contains=parts[2]))

    return rules


def list_tracked_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def should_ignore(path: str, check_id: str, line: str, rules: list[AllowRule]) -> bool:
    return any(
        rule.path == path and rule.check_id == check_id and rule.contains in line for rule in rules
    )


def main() -> int:
    root = repo_root()
    allowlist_path = Path(__file__).resolve().with_name("legacy_workspace_guard_allowlist.txt")

    checks = [
        Check(
            id="legacy_workspace_html_route",
            description='Legacy HTML workspace route decorator @api_router.get("/workspace")',
            pattern=re.compile(r'@api_router\.get\("/workspace"\)'),
        ),
        Check(
            id="legacy_workspace_query_entrypoint",
            description="Legacy query-string entrypoint /workspace?",
            pattern=re.compile(r"(?<!/api)(?<!/api/v1)/workspace\?"),
        ),
        Check(
            id="legacy_workspace_redirect_helper",
            description="Legacy redirect helper _workspace_redirect_to_spa",
            pattern=re.compile(r"_workspace_redirect_to_spa"),
        ),
        Check(
            id="legacy_workspace_js_asset",
            description="Legacy shell asset reference workspace.js",
            pattern=re.compile(r"(?<![A-Za-z0-9_.-])workspace\.js(?![A-Za-z0-9_.-])"),
        ),
        Check(
            id="legacy_workspace_css_asset",
            description="Legacy shell asset reference workspace.css",
            pattern=re.compile(r"(?<![A-Za-z0-9_.-])workspace\.css(?![A-Za-z0-9_.-])"),
        ),
    ]

    allow_rules = load_allowlist(allowlist_path)
    violations: list[str] = []

    for rel_path in list_tracked_files(root):
        if not rel_path.startswith("apps/web/"):
            continue
        if rel_path in {
            "apps/web/scripts/check_legacy_workspace_artifacts.py",
            "apps/web/scripts/legacy_workspace_guard_allowlist.txt",
        }:
            continue

        file_path = root / rel_path
        if file_path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            for check in checks:
                if check.pattern.search(line) and not should_ignore(
                    rel_path, check.id, line, allow_rules
                ):
                    violations.append(
                        f"{rel_path}:{line_no} [{check.id}] {check.description}\n    {line.strip()}"
                    )

    if violations:
        print("Legacy workspace artifact guard failed. Found banned patterns:\n")
        print("\n".join(violations))
        print(f"\nIf intentional, add a scoped exception to {allowlist_path.relative_to(root)}")
        return 1

    print("Legacy workspace artifact guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
