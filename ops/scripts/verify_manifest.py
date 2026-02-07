#!/usr/bin/env python3
"""Verify that all files listed in data/seed/manifest.csv match their recorded SHA-256.

Usage:
  python scripts/verify_manifest.py

Exits non-zero if any mismatch or missing file is detected.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "data" / "seed" / "manifest.csv"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not MANIFEST.exists():
        print(f"ERROR: Manifest not found: {MANIFEST}", file=sys.stderr)
        return 2

    mismatches = 0
    missing = 0
    checked = 0

    with MANIFEST.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            checked += 1
            expected = (row.get("sha256") or "").strip()
            rel_path = (row.get("repo_path") or "").strip()

            if not expected or not rel_path:
                print(f"WARN: Skipping malformed row: {row}")
                continue

            target = REPO_ROOT / rel_path
            if not target.exists():
                print(f"MISSING: {rel_path}")
                missing += 1
                continue

            actual = sha256_file(target)
            if actual.lower() != expected.lower():
                print("MISMATCH:", rel_path)
                print("  expected:", expected)
                print("  actual:  ", actual)
                mismatches += 1

    if missing == 0 and mismatches == 0:
        print(f"OK: Verified {checked} file(s) against {MANIFEST.relative_to(REPO_ROOT)}")
        return 0

    print(f"FAILED: checked={checked} missing={missing} mismatches={mismatches}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
