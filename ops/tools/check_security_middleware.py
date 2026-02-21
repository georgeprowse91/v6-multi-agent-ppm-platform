#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.tools.security_baseline_checks import check_service_security_middleware, format_violations


def main() -> int:
    violations = check_service_security_middleware()
    if violations:
        print(format_violations(violations))
        return 1
    print("Security middleware baseline checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
