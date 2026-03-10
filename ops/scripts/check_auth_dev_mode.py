"""Verify AUTH_DEV_MODE is not enabled in any deployment configuration.

Scans Helm values.yaml, Kubernetes manifests, and Terraform tfvars to ensure
AUTH_DEV_MODE is never set to true in deployment configs that could reach
staging or production.

Usage:
    python ops/scripts/check_auth_dev_mode.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = [
    REPO_ROOT / "services",
    REPO_ROOT / "apps",
    REPO_ROOT / "ops" / "infra",
]

# Files that are expected to reference AUTH_DEV_MODE for documentation only
ALLOW_LIST = {
    "ops/config/.env.example",
    "ops/tools/check_config_parity.py",
}

PATTERN = re.compile(
    r"""AUTH_DEV_MODE["']?\s*[:=]\s*["']?true["']?""",
    re.IGNORECASE,
)


def scan_file(path: Path) -> list[tuple[int, str]]:
    """Return (line_number, line) pairs where AUTH_DEV_MODE is set to true."""
    hits: list[tuple[int, str]] = []
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return hits
    for i, line in enumerate(text.splitlines(), start=1):
        if PATTERN.search(line):
            hits.append((i, line.strip()))
    return hits


def main() -> int:
    print("Scanning deployment configs for AUTH_DEV_MODE=true ...\n")
    violations: list[str] = []

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for ext in ("*.yaml", "*.yml", "*.tfvars", "*.tf", "*.json", "*.env"):
            for path in scan_dir.rglob(ext):
                rel = path.relative_to(REPO_ROOT)
                if str(rel) in ALLOW_LIST:
                    continue
                hits = scan_file(path)
                for lineno, line in hits:
                    msg = f"  FAIL  {rel}:{lineno}: {line}"
                    print(msg)
                    violations.append(msg)

    print()
    if violations:
        print(
            f"{len(violations)} violation(s) found: AUTH_DEV_MODE must not be "
            "true in deployment configs."
        )
        return 1

    print("No AUTH_DEV_MODE violations found in deployment configs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
