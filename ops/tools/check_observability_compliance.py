from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from ops.tools.observability_compliance_checks import (  # noqa: E402
    check_service_observability_compliance,
    format_violations,
)


def main() -> int:
    violations = check_service_observability_compliance()
    if violations:
        print(format_violations(violations))
        return 1
    print("Observability baseline checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
