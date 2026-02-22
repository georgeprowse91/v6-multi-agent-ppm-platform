#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    allowed_paths: tuple[re.Pattern[str], ...] = ()
    allowed_line_patterns: tuple[re.Pattern[str], ...] = ()


RULES: tuple[Rule, ...] = (
    Rule(
        name="legacy workspace html route token (/workspace)",
        pattern=re.compile(r"(?<!/api)(?<!/api/v1)/workspace(?![a-zA-Z])"),
        allowed_paths=(
            re.compile(r"^apps/web/src/legacy_main\.py$"),
            re.compile(r"^apps/web/tests/test_oidc_login_flow\.py$"),
            re.compile(r"^apps/web/tests/test_workspace_shell\.py$"),
            re.compile(r"^apps/web/tests/test_demo_mode\.py$"),
            re.compile(r"^apps/web/README\.md$"),
            re.compile(r"^docs/ui/UI_COVERAGE_MATRIX\.md$"),
            re.compile(r"^\.devcontainer/devcontainer\.json$"),
            re.compile(r"^\.github/renovate\.json$"),
            re.compile(r"^artifacts/.*\.json$"),
        ),
        allowed_line_patterns=(
            re.compile(r"/api/workspace"),
            re.compile(r"/workspaces"),
            re.compile(r"/v1/workspace"),
            re.compile(r"return_to=/workspace"),
            re.compile(r"without relying on `/workspace` HTML routes"),
            re.compile(r"/workspace HTML entrypoints"),
        ),
    ),
    Rule(name="legacy bundle name workspace.js", pattern=re.compile(r"workspace\.js")),
    Rule(name="legacy bundle name workspace.css", pattern=re.compile(r"workspace\.css")),
    Rule(name="legacy env flag LEGACY_UI_ENABLED", pattern=re.compile(r"LEGACY_UI_ENABLED")),
    Rule(name="legacy env flag INTERNAL_LEGACY_UI_ENABLED", pattern=re.compile(r"INTERNAL_LEGACY_UI_ENABLED")),
    Rule(name="legacy helper _legacy_route_or_redirect", pattern=re.compile(r"_legacy_route_or_redirect")),
)

TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".scss", ".md", ".json", ".yaml", ".yml", ".toml", ".sh", ".html"
}


def _is_allowed(rule: Rule, path: str, line: str) -> bool:
    if any(p.search(path) for p in rule.allowed_paths):
        return True
    return any(p.search(line) for p in rule.allowed_line_patterns)


def _tracked_files() -> list[str]:
    output = subprocess.run([
        "git", "ls-files"
    ], check=True, capture_output=True, text=True)
    return [line.strip() for line in output.stdout.splitlines() if line.strip()]


def main() -> int:
    violations: list[str] = []
    for rel in _tracked_files():
        path = Path(rel)
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            for rule in RULES:
                if not rule.pattern.search(line):
                    continue
                if _is_allowed(rule, rel, line):
                    continue
                violations.append(f"{rel}:{line_no}: banned {rule.name}: {line.strip()}")

    if violations:
        print("Legacy UI reference check failed. Remove or whitelist these references:", file=sys.stderr)
        for violation in violations:
            print(f" - {violation}", file=sys.stderr)
        return 1

    print("Legacy UI reference check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
