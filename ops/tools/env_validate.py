from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

SERVICES: dict[str, tuple[str, str]] = {
    "api-gateway": ("services/api-gateway/src", "api.config"),
    "orchestration-service": ("services/orchestration-service/src", "config"),
    "document-service": ("services/document-service/src", "config"),
    "workflow-service": ("services/workflow-service/src", "config"),
    "analytics-service": ("services/analytics-service/src", "config"),
    "web": ("apps/web/src", "config"),
}


def validate_service(name: str, src_rel: str, module_name: str) -> tuple[bool, str]:
    src_path = str(REPO_ROOT / src_rel)
    sys.path.insert(0, src_path)
    try:
        module = importlib.import_module(module_name)
        module.validate_startup_config()
        return True, f"[{name}] OK"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    finally:
        if sys.path and sys.path[0] == src_path:
            sys.path.pop(0)


def main() -> int:
    os.environ.setdefault("ENV_VALIDATE_DRY_RUN", "1")
    failures: list[str] = []
    for name, (src_rel, module_name) in SERVICES.items():
        ok, output = validate_service(name, src_rel, module_name)
        print(output)
        if not ok:
            failures.append(name)

    if failures:
        print(f"\nValidation failed for: {', '.join(failures)}")
        return 1
    print("\nAll service environment schemas validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
