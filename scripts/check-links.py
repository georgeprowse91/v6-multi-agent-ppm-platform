#!/usr/bin/env python3
"""Check markdown links for missing files and anchors."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

LINK_PATTERN = re.compile(r"!?(\[[^\]]*\]\(([^)]+)\))")


def strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks to avoid false-positive link checks."""
    lines = text.splitlines()
    output: list[str] = []
    in_code_block = False
    fence = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_code_block:
                in_code_block = True
                fence = marker
            elif marker == fence:
                in_code_block = False
                fence = ""
            continue
        if not in_code_block:
            output.append(line)
    return "\n".join(output)


SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pnpm-store",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


def iter_markdown_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def parse_link_destination(raw: str) -> str:
    dest = raw.strip()
    if " " in dest:
        dest = dest.split(" ", 1)[0]
    return dest


def is_external_link(dest: str) -> bool:
    return dest.startswith(("http://", "https://", "mailto:", "tel:"))


def slugify_heading(text: str, existing: dict[str, int]) -> str:
    heading = text.strip().lower()
    heading = re.sub(r"[`~!@#$%^&*()+=\[\]{}\\|;:\"',.<>/?]", "", heading)
    heading = re.sub(r"\s+", "-", heading)
    if heading in existing:
        existing[heading] += 1
        return f"{heading}-{existing[heading]}"
    existing[heading] = 0
    return heading


def extract_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return anchors
    for idx, line in enumerate(lines):
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            if heading:
                anchors.add(slugify_heading(heading, counts))
        elif idx + 1 < len(lines):
            next_line = lines[idx + 1]
            if line and set(next_line.strip()) in ({"-"}, {"="}):
                anchors.add(slugify_heading(line.strip(), counts))
    return anchors


def resolve_target(source: Path, path_part: str) -> Path:
    if path_part.startswith("/"):
        return ROOT / path_part.lstrip("/")
    return (source.parent / path_part).resolve()


def check_links() -> list[dict[str, str]]:
    broken: list[dict[str, str]] = []
    anchor_cache: dict[Path, set[str]] = {}

    for md_file in iter_markdown_files(ROOT):
        text = strip_code_blocks(md_file.read_text(encoding="utf-8", errors="ignore"))
        for match in LINK_PATTERN.finditer(text):
            raw_dest = match.group(2)
            dest = parse_link_destination(raw_dest)
            if not dest or is_external_link(dest):
                continue
            if dest.startswith("#"):
                anchor = dest[1:]
                anchors = anchor_cache.setdefault(md_file, extract_anchors(md_file))
                if anchor and anchor not in anchors:
                    broken.append(
                        {
                            "source": str(md_file.relative_to(ROOT)),
                            "link": match.group(1),
                            "destination": dest,
                            "reason": "missing anchor",
                        }
                    )
                continue
            dest = unquote(dest)
            if "#" in dest:
                path_part, anchor = dest.split("#", 1)
            else:
                path_part, anchor = dest, ""
            if not path_part:
                continue
            target = resolve_target(md_file, path_part)
            if not target.exists():
                broken.append(
                    {
                        "source": str(md_file.relative_to(ROOT)),
                        "link": match.group(1),
                        "destination": dest,
                        "reason": "missing file",
                    }
                )
                continue
            if anchor:
                anchors = anchor_cache.setdefault(target, extract_anchors(target))
                if anchor not in anchors:
                    broken.append(
                        {
                            "source": str(md_file.relative_to(ROOT)),
                            "link": match.group(1),
                            "destination": dest,
                            "reason": "missing anchor",
                        }
                    )
    return broken


def main() -> int:
    parser = argparse.ArgumentParser(description="Check markdown links for missing files/anchors")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    broken = check_links()

    if args.format == "json":
        import json

        print(json.dumps(broken, indent=2))
    else:
        if broken:
            print("Broken markdown links detected:\n")
        for item in broken:
            print(f"{item['source']}: {item['destination']} ({item['reason']}) | {item['link']}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
