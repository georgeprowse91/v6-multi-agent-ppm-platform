#!/usr/bin/env python3
"""Validate template files, methodology maps, and catalog links."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to run check-templates.py") from exc

ROOT = Path(__file__).resolve().parents[1]
LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"

TEMPLATE_DIRS = [
    ROOT / "docs" / "methodology" / "agile" / "templates",
    ROOT / "docs" / "methodology" / "waterfall" / "templates",
    ROOT / "docs" / "methodology" / "hybrid" / "templates",
    ROOT / "docs" / "templates" / "shared",
    ROOT / "services" / "notification-service" / "templates",
]

EXTRA_TEMPLATES = [ROOT / "docs" / "compliance" / "privacy-dpia-template.md"]


def iter_template_files() -> Iterable[Path]:
    for directory in TEMPLATE_DIRS:
        if directory.exists():
            yield from (path for path in directory.iterdir() if path.is_file())
    for path in EXTRA_TEMPLATES:
        if path.exists():
            yield path


def is_lfs_pointer(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            head = handle.read(200)
    except OSError:
        return False
    return LFS_POINTER in head


def is_header_only_csv(path: Path) -> bool:
    lines = [line for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
    return len(lines) <= 1


def is_empty_yaml(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return True
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return False
    if data in (None, [], {}):
        return True
    return False


def check_templates() -> list[str]:
    errors: list[str] = []
    lfs_warnings: list[str] = []
    for path in iter_template_files():
        if path.stat().st_size == 0:
            errors.append(f"Template is empty: {path.relative_to(ROOT)}")
            continue
        if is_lfs_pointer(path):
            # LFS pointers are expected in CI without LFS checkout; warn but don't fail
            lfs_warnings.append(f"Template is LFS pointer (run 'git lfs pull'): {path.relative_to(ROOT)}")
            continue
        if path.suffix.lower() == ".csv" and is_header_only_csv(path):
            errors.append(f"CSV template has no data rows: {path.relative_to(ROOT)}")
        if path.suffix.lower() in {".yaml", ".yml"} and is_empty_yaml(path):
            errors.append(f"YAML template is empty: {path.relative_to(ROOT)}")
    # Print LFS warnings but don't fail on them
    for warning in lfs_warnings:
        print(f"[LFS] {warning}")
    return errors


def iter_yaml_templates(data: dict) -> Iterable[str]:
    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "template" and isinstance(item, str):
                    yield item
                else:
                    yield from visit(item)
        elif isinstance(value, list):
            for item in value:
                yield from visit(item)

    yield from visit(data)


def check_methodology_files() -> list[str]:
    errors: list[str] = []
    for path in ROOT.glob("docs/methodology/*/map.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore"))
        if not data or not data.get("stages"):
            errors.append(f"Map file has no stages: {path.relative_to(ROOT)}")
            continue
        for template in iter_yaml_templates(data):
            target = (ROOT / template).resolve()
            if not target.exists():
                errors.append(
                    f"Map template reference missing: {path.relative_to(ROOT)} -> {template}"
                )

    for path in ROOT.glob("docs/methodology/*/gates.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore"))
        if not data or not data.get("gates"):
            errors.append(f"Gate file has no gates: {path.relative_to(ROOT)}")
            continue
        for template in iter_yaml_templates(data):
            target = (ROOT / template).resolve()
            if not target.exists():
                errors.append(
                    f"Gate template reference missing: {path.relative_to(ROOT)} -> {template}"
                )

    return errors


def check_template_catalog() -> list[str]:
    errors: list[str] = []
    catalog = ROOT / "docs" / "product" / "templates-catalog.md"
    if not catalog.exists():
        errors.append("Template catalog missing: docs/product/templates-catalog.md")
        return errors
    content = catalog.read_text(encoding="utf-8", errors="ignore")
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", content):
        dest = match.group(1)
        if dest.startswith("http"):
            continue
        target = (catalog.parent / dest).resolve()
        if not target.exists():
            errors.append(
                f"Template catalog link missing: {catalog.relative_to(ROOT)} -> {dest}"
            )
    return errors


def main() -> int:
    errors = []
    errors.extend(check_templates())
    errors.extend(check_methodology_files())
    errors.extend(check_template_catalog())

    if errors:
        print("Template validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Template validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
