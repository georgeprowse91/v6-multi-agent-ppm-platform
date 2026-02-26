#!/usr/bin/env python3
"""Quickstart smoke test — verifies that core modules can be imported."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

CORE_MODULES = [
    "agents",
    "apps",
    "packages",
]


def main() -> int:
    failures: list[str] = []
    checked = 0
    for module_dir in CORE_MODULES:
        module_path = REPO_ROOT / module_dir
        if not module_path.exists():
            continue
        init = module_path / "__init__.py"
        if init.exists():
            checked += 1
            try:
                importlib.import_module(module_dir)
            except Exception as exc:
                failures.append(f"{module_dir}: {exc}")

    # Also verify the schema tool can be loaded
    schema_tool = REPO_ROOT / "scripts" / "schema_tool.py"
    if schema_tool.exists():
        checked += 1
        try:
            spec = importlib.util.spec_from_file_location("schema_tool", schema_tool)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
        except Exception as exc:
            failures.append(f"scripts/schema_tool.py: {exc}")

    if failures:
        print("Quickstart smoke failures:")
        for f in failures:
            print(f"  {f}")
        return 1

    print(f"Quickstart smoke passed ({checked} modules checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
