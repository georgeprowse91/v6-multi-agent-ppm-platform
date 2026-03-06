#!/usr/bin/env python3
"""Build dependency map of legacy template references across tracked files."""

from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "docs/templates/migration/legacy-to-canonical.csv"
OUT_PATH = ROOT / "docs/templates/migration/dependency-map.json"

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


REQUIRED_SCAN_PATHS = [
    "docs/templates/README.md",
    "docs/templates/index.json",
]

REQUIRED_SCAN_PREFIXES = [
    "docs/templates/standards/",
    "docs/",
    "scripts/",
]


def git_tracked_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    files = [Path(line.strip()) for line in proc.stdout.splitlines() if line.strip()]

    filtered: list[Path] = []
    for file in files:
        p = file.as_posix()
        if p.startswith("docs/") or p.startswith("scripts/"):
            filtered.append(file)
    return filtered


def load_legacy_map() -> list[dict[str, str]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return rows


def is_probably_text(content: bytes) -> bool:
    return b"\x00" not in content


def classify_line_reference(line: str, legacy_path: str, basename: str) -> str | None:
    if legacy_path in line:
        return "exact path"

    for match in MARKDOWN_LINK_RE.finditer(line):
        destination = match.group(1).split("#", 1)[0].strip()
        if not destination:
            continue
        if destination == basename or destination.endswith(f"/{basename}"):
            return "relative link"

    basename_pattern = re.compile(rf"(?<![\w./-]){re.escape(basename)}(?![\w./-])")
    if basename_pattern.search(line):
        return "plain-text mention"
    return None


def main() -> None:
    legacy_rows = load_legacy_map()
    tracked_files = git_tracked_files()

    legacy_lookup = {
        row["old_path"]: {
            "new_path": row["new_path"],
            "basename": Path(row["old_path"]).name,
        }
        for row in legacy_rows
    }

    references: list[dict[str, object]] = []
    summary: dict[str, dict[str, object]] = {
        old_path: {
            "legacy_doc": old_path,
            "planned_replacement_target": info["new_path"],
            "reference_count": 0,
        }
        for old_path, info in legacy_lookup.items()
    }

    for rel_path in tracked_files:
        full_path = ROOT / rel_path
        try:
            raw = full_path.read_bytes()
        except OSError:
            continue

        if not is_probably_text(raw):
            continue

        text = raw.decode("utf-8", errors="ignore")
        lines = text.splitlines()

        for old_path, info in legacy_lookup.items():
            basename = info["basename"]
            for line_no, line in enumerate(lines, start=1):
                reference_type = classify_line_reference(line, old_path, basename)
                if reference_type is None:
                    continue
                if rel_path.as_posix() == old_path:
                    continue

                references.append(
                    {
                        "legacy_doc": old_path,
                        "referencing_file": rel_path.as_posix(),
                        "reference_type": reference_type,
                        "planned_replacement_target": info["new_path"],
                        "line": line_no,
                    }
                )
                summary[old_path]["reference_count"] = int(summary[old_path]["reference_count"]) + 1

    unresolved = [r for r in references if not r["planned_replacement_target"]]

    deletion_gate = {
        "blocked": bool(references),
        "reason": "References to legacy files still exist; do not delete legacy files until all listed references are migrated.",
        "all_references_have_planned_replacements": not unresolved,
    }

    tracked_file_set = {p.as_posix() for p in tracked_files}
    required_coverage = [
        {"path": path, "present_in_scan": path in tracked_file_set}
        for path in REQUIRED_SCAN_PATHS
    ]

    payload = {
        "source_csv": CSV_PATH.relative_to(ROOT).as_posix(),
        "generated_by": Path(__file__).relative_to(ROOT).as_posix(),
        "scan_scope": {
            "tracked_prefixes": REQUIRED_SCAN_PREFIXES,
            "required_paths": required_coverage,
            "scanned_file_count": len(tracked_files),
        },
        "deletion_gate": deletion_gate,
        "legacy_summary": list(summary.values()),
        "references": sorted(
            references,
            key=lambda item: (
                item["legacy_doc"],
                item["referencing_file"],
                int(item["line"]),
            ),
        ),
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
