from __future__ import annotations

import asyncio
import sys

from full_platform_demo_run import run_full_platform_demo


if __name__ == "__main__":
    try:
        asyncio.run(run_full_platform_demo())
    except Exception:  # noqa: BLE001
        sys.exit(1)
