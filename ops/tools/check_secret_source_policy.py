#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.tools.security_baseline_checks import check_secret_resolution_usage, format_violations


def main() -> int:
    violations = check_secret_resolution_usage()
    if violations:
        print(format_violations(violations))
        return 1
    print("Secret source policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
