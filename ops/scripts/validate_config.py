import sys
from pathlib import Path

from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from api.config import Settings  # noqa: E402


def main() -> int:
    try:
        Settings()
    except ValidationError as err:
        print("Configuration validation failed:")
        print(err)
        return 1

    print("Configuration OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
