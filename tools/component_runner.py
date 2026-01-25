from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Describe a service or app component.")
    parser.add_argument("--component-type", required=True, choices=["app", "service"])
    parser.add_argument("--component-name", required=True)
    parser.add_argument("--component-root", required=True)
    parser.add_argument("--json", action="store_true", help="Output summary as JSON.")
    return parser.parse_args()


def _summarize_component(root: Path, component_type: str, name: str) -> dict[str, Any]:
    readme = root / "README.md"
    summary_lines = []
    if readme.exists():
        summary_lines = readme.read_text().splitlines()[:6]

    src_dir = root / "src"
    entrypoints = []
    if src_dir.exists():
        entrypoints = [p.name for p in src_dir.glob("*.py") if p.name != "__init__.py"]

    summary = {
        "component_type": component_type,
        "component_name": name,
        "root": str(root),
        "has_tests": (root / "tests").exists(),
        "entrypoints": entrypoints,
        "readme_excerpt": "\n".join(summary_lines).strip(),
    }
    return summary


def main() -> None:
    args = _parse_args()
    root = Path(args.component_root).resolve()
    summary = _summarize_component(root, args.component_type, args.component_name)
    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print(f"{summary['component_type'].title()}: {summary['component_name']}")
    print(f"Root: {summary['root']}")
    print(f"Has tests: {summary['has_tests']}")
    if summary["entrypoints"]:
        print(f"Entrypoints: {', '.join(summary['entrypoints'])}")
    if summary["readme_excerpt"]:
        print("README excerpt:")
        print(summary["readme_excerpt"])


if __name__ == "__main__":
    main()
