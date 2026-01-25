#!/usr/bin/env python3
"""Repair markdown lead-ins in docs_markdown/.

Rules:
- Skip YAML frontmatter and fenced code blocks.
- Fix colon-hyphen artifacts at line start / list item start.
- Convert em/en dash lead-ins to **Lead-in:**.
- Bold plain lead-ins followed by a colon.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re

DOCS_ROOT = Path("docs_markdown")

LIST_PREFIX_RE = re.compile(r"^(\s*(?:[-*+]\s+|\d+\.\s+))(.*)$")

BOLD_ARTIFACT_RE = re.compile(r"^\*\*([^*]+?)\:\*\*\s*-\s*(.+)$")
NONBOLD_ARTIFACT_RE = re.compile(r"^([^:]{1,120}?):\s*-\s*(.+)$")
NONBOLD_ARTIFACT_TIGHT_RE = re.compile(r"^([^:]{1,120}?):-\s*(.+)$")
DASH_LEADIN_RE = re.compile(r"^(.+?)\s*[—–]\s+(.+)$")
PLAIN_COLON_RE = re.compile(r"^([^:]{1,120}?):\s+(.+)$")


@dataclass
class Counts:
    artifact_fixes: int = 0
    leadin_conversions: int = 0


def is_heading_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("#")


def is_blockquote_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith(">")


def is_table_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("|")


def is_valid_leadin(text: str, require_uppercase: bool = False) -> bool:
    stripped = text.strip()
    if len(stripped) == 0:
        return False
    if len(text) > 120:
        return False
    if "—" in text or "–" in text:
        return False
    if " - " in text:
        return False
    if stripped.startswith("#"):
        return False
    if "http://" in text or "https://" in text:
        return False
    if "`" in text:
        return False
    if require_uppercase and not stripped[0].isupper():
        return False
    return True


def split_prefix(line: str) -> tuple[str, str]:
    match = LIST_PREFIX_RE.match(line)
    if match:
        return match.group(1), match.group(2)
    return "", line


def process_line(line: str, counts: Counts) -> str:
    if is_heading_line(line) or is_blockquote_line(line) or is_table_line(line):
        return line

    prefix, body = split_prefix(line)

    bold_artifact = BOLD_ARTIFACT_RE.match(body)
    if bold_artifact:
        lead, desc = bold_artifact.group(1).strip(), bold_artifact.group(2).strip()
        counts.artifact_fixes += 1
        return f"{prefix}**{lead}:** {desc}\n"

    nonbold_artifact = NONBOLD_ARTIFACT_RE.match(body) or NONBOLD_ARTIFACT_TIGHT_RE.match(body)
    if nonbold_artifact:
        lead, desc = nonbold_artifact.group(1).strip(), nonbold_artifact.group(2).strip()
        if is_valid_leadin(lead):
            counts.artifact_fixes += 1
            counts.leadin_conversions += 1
            return f"{prefix}**{lead}:** {desc}\n"

    dash_match = DASH_LEADIN_RE.match(body)
    if dash_match:
        lead, desc = dash_match.group(1).strip(), dash_match.group(2).strip()
        if lead.startswith("**"):
            return line
        if not is_valid_leadin(lead):
            return line
        if ":" in lead:
            return line
        counts.leadin_conversions += 1
        return f"{prefix}**{lead}:** {desc}\n"

    plain_colon = PLAIN_COLON_RE.match(body)
    if plain_colon:
        lead, desc = plain_colon.group(1).strip(), plain_colon.group(2).strip()
        if lead.startswith("**"):
            return line
        if desc.startswith("-"):
            return line
        if not is_valid_leadin(lead, require_uppercase=True):
            return line
        counts.leadin_conversions += 1
        return f"{prefix}**{lead}:** {desc}\n"

    return line


def process_file(path: Path) -> tuple[str, Counts, int]:
    counts = Counts()
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = []

    in_frontmatter = False
    in_codefence = False

    for idx, line in enumerate(lines):
        stripped = line.rstrip("\n")
        if idx == 0 and stripped == "---":
            in_frontmatter = True
            new_lines.append(line)
            continue
        if in_frontmatter:
            new_lines.append(line)
            if stripped == "---":
                in_frontmatter = False
            continue

        if stripped.startswith("```"):
            in_codefence = not in_codefence
            new_lines.append(line)
            continue

        if in_codefence:
            new_lines.append(line)
            continue

        new_lines.append(process_line(line, counts))

    if new_lines != lines:
        path.write_text("".join(new_lines), encoding="utf-8")
    change_count = sum(1 for a, b in zip(lines, new_lines) if a != b)
    return path.as_posix(), counts, change_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=DOCS_ROOT.as_posix())
    args = parser.parse_args()

    root = Path(args.root)
    files = sorted(root.rglob("*.md"))

    total_counts = Counts()
    changed_files = []

    for path in files:
        _, counts, change_count = process_file(path)
        if change_count:
            changed_files.append((path, change_count))
            total_counts.artifact_fixes += counts.artifact_fixes
            total_counts.leadin_conversions += counts.leadin_conversions

    print("Per-file change counts:")
    for path, change_count in sorted(changed_files, key=lambda x: (-x[1], x[0].as_posix())):
        print(f"{path.as_posix()}: {change_count}")
    print("---")
    print(f"Total files changed: {len(changed_files)}")
    print(f"Total ': -' artifact fixes: {total_counts.artifact_fixes}")
    print(f"Total lead-in conversions: {total_counts.leadin_conversions}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
