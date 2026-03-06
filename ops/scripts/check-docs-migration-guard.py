#!/usr/bin/env python3
"""Docs migration guard for legacy template path retirement policy."""

from __future__ import annotations

import csv
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAPPING_CSV = ROOT / "docs/templates/migration/legacy-to-canonical.csv"

GUIDANCE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "docs/templates/README.md": (
        "migration/legacy-to-canonical.csv",
        "redirect stubs",
        "one-to-one",
    ),
    "docs/templates/standards/index-governance.md": (
        "Add/refresh migration guidance",
        "docs/templates/README.md",
        "template-naming-rules.md",
    ),
    "docs/templates/standards/template-naming-rules.md": (
        "resolves to exactly one canonical template ID",
        "Examples: Legacy → Canonical Mappings",
    ),
}

REFERENCE_SCAN_EXCLUDES = {
    "docs/templates/migration/legacy-to-canonical.csv",
    "docs/templates/migration/dependency-map.json",
}


@dataclass(frozen=True)
class MappingRow:
    row_number: int
    old_path: str
    raw_new_path: str
    canonical_targets: tuple[str, ...]


def parse_primary_canonical_target(raw_new_path: str) -> tuple[str, ...]:
    candidate = raw_new_path.split("(", 1)[0].strip()
    candidate = candidate.split(" ", 1)[0].strip()
    if not candidate:
        return ()
    return (candidate,)


def git_tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [p for p in proc.stdout.decode("utf-8").split("\x00") if p]


def is_text_file(path: Path) -> bool:
    try:
        return b"\x00" not in path.read_bytes()[:4096]
    except OSError:
        return False


def load_mapping_rows() -> list[MappingRow]:
    with MAPPING_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows: list[MappingRow] = []
        for index, row in enumerate(reader, start=2):
            old_path = (row.get("old_path") or "").strip()
            raw_new_path = (row.get("new_path") or "").strip()
            targets = parse_primary_canonical_target(raw_new_path)
            rows.append(
                MappingRow(
                    row_number=index,
                    old_path=old_path,
                    raw_new_path=raw_new_path,
                    canonical_targets=targets,
                )
            )
    return rows


def fail_with_header(header: str) -> None:
    print(f"docs migration guard failed: {header}")


def check_deleted_legacy_references(rows: list[MappingRow], tracked_files: list[str]) -> bool:
    deleted_legacy_paths = [row.old_path for row in rows if row.old_path and not (ROOT / row.old_path).exists()]
    if not deleted_legacy_paths:
        return True

    text_files = [
        rel
        for rel in tracked_files
        if rel not in REFERENCE_SCAN_EXCLUDES and is_text_file(ROOT / rel)
    ]
    offenders: dict[str, set[str]] = defaultdict(set)

    for rel in text_files:
        full_path = ROOT / rel
        content = full_path.read_text(encoding="utf-8", errors="ignore")
        for legacy_path in deleted_legacy_paths:
            if legacy_path in content:
                offenders[rel].add(legacy_path)

    if not offenders:
        return True

    fail_with_header("deleted legacy path references were found")
    print("Offending files and unmatched legacy references:")
    for rel in sorted(offenders):
        print(f"  - {rel}")
        for legacy in sorted(offenders[rel]):
            print(f"      * {legacy}")
    return False


def check_mapping_resolves_exactly_one_target(rows: list[MappingRow]) -> bool:
    row_failures = [row for row in rows if len(row.canonical_targets) != 1]

    old_path_to_targets: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        old_path_to_targets[row.old_path].update(row.canonical_targets)

    duplicate_failures = {
        old_path: sorted(targets)
        for old_path, targets in old_path_to_targets.items()
        if len(targets) != 1
    }

    if not row_failures and not duplicate_failures:
        return True

    fail_with_header("each legacy mapping row must resolve to exactly one canonical target")
    if row_failures:
        print("Rows with invalid canonical target count:")
        for row in row_failures:
            print(
                f"  - row {row.row_number}: {row.old_path} -> {row.raw_new_path!r} "
                f"(resolved targets: {list(row.canonical_targets)})"
            )
    if duplicate_failures:
        print("Legacy paths resolving to multiple canonical targets:")
        for old_path, targets in sorted(duplicate_failures.items()):
            print(f"  - {old_path}: {targets}")
    return False


def check_canonical_targets_exist(rows: list[MappingRow]) -> bool:
    missing: list[tuple[int, str, str]] = []
    for row in rows:
        if len(row.canonical_targets) != 1:
            continue
        target = row.canonical_targets[0]
        if not (ROOT / target).exists():
            missing.append((row.row_number, row.old_path, target))

    if not missing:
        return True

    fail_with_header("canonical targets from migration mappings are missing")
    for row_number, old_path, target in missing:
        print(f"  - row {row_number}: {old_path} -> missing {target}")
    return False


def check_migration_guidance_docs() -> bool:
    missing_markers: dict[str, list[str]] = {}
    missing_files: list[str] = []

    for rel, markers in GUIDANCE_REQUIREMENTS.items():
        path = ROOT / rel
        if not path.exists():
            missing_files.append(rel)
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        absent = [marker for marker in markers if marker not in text]
        if absent:
            missing_markers[rel] = absent

    if not missing_files and not missing_markers:
        return True

    fail_with_header("migration guidance documentation is out of date")
    if missing_files:
        print("Missing required guidance files:")
        for rel in sorted(missing_files):
            print(f"  - {rel}")
    if missing_markers:
        print("Files missing required migration guidance markers:")
        for rel in sorted(missing_markers):
            print(f"  - {rel}")
            for marker in missing_markers[rel]:
                print(f"      * missing marker: {marker}")
    return False


def main() -> int:
    rows = load_mapping_rows()
    tracked_files = git_tracked_files()

    checks = [
        lambda: check_deleted_legacy_references(rows, tracked_files),
        lambda: check_mapping_resolves_exactly_one_target(rows),
        lambda: check_canonical_targets_exist(rows),
        check_migration_guidance_docs,
    ]

    for check in checks:
        if not check():
            return 1

    print("docs migration guard: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
