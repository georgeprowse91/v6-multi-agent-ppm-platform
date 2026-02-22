#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

import yaml


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifests = sorted((root / "integrations" / "connectors").glob("*/manifest.yaml"))
    failures: list[str] = []
    for manifest_path in manifests:
        data = yaml.safe_load(manifest_path.read_text())
        maturity = data.get("maturity") or {}
        level = maturity.get("level", 0)
        caps = maturity.get("capabilities") or {}
        if level >= 2:
            required_true = ["read", "write", "idempotent_write", "conflict_handling"]
            missing = [item for item in required_true if not caps.get(item)]
            if missing:
                failures.append(f"{data.get('id', manifest_path.parent.name)} missing: {', '.join(missing)}")

    if failures:
        print("Connector maturity check failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print(f"Connector maturity check passed for {len(manifests)} manifests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
