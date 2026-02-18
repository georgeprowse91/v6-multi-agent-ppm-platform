import sys
from pathlib import Path

from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
API_GATEWAY_SRC = REPO_ROOT / "apps" / "api-gateway" / "src"
for root in (REPO_ROOT, API_GATEWAY_SRC):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

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
