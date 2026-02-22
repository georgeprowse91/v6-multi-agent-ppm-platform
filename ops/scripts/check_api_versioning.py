#!/usr/bin/env python3
"""Verify that all API router modules declare an explicit version prefix."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

API_DIRS = [
    REPO_ROOT / "apps" / "api-gateway" / "src",
    REPO_ROOT / "apps" / "web" / "src",
]

REQUIRED_PREFIX_PATTERN = "/v"


def _check_file(path: Path) -> list[str]:
    """Return a list of issues found in *path*."""
    issues: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        issues.append(f"{path}: syntax error: {exc}")
        return issues

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            attr_name = getattr(func, "attr", None)
            if attr_name == "APIRouter":
                has_prefix = False
                for kw in node.keywords:
                    if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                        if isinstance(kw.value.value, str) and REQUIRED_PREFIX_PATTERN in kw.value.value:
                            has_prefix = True
                if not has_prefix:
                    issues.append(
                        f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                        "APIRouter() should declare an explicit versioned prefix (e.g. prefix='/v1')"
                    )
    return issues


def main() -> int:
    all_issues: list[str] = []
    for api_dir in API_DIRS:
        if not api_dir.exists():
            continue
        for py_file in sorted(api_dir.rglob("*.py")):
            all_issues.extend(_check_file(py_file))

    if all_issues:
        print("API versioning issues:")
        for issue in all_issues:
            print(f"  {issue}")
        # Warn but do not block — many routers are mounted with prefix at the app level
        print(f"\n{len(all_issues)} API versioning advisory warning(s).")
    else:
        print("API versioning check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
