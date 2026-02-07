from __future__ import annotations

import argparse
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Export audit evidence pack")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--output", type=Path, default=Path("audit-evidence.zip"))
    args = parser.parse_args()

    headers = {
        "Authorization": f"Bearer {args.token}",
        "X-Tenant-ID": args.tenant_id,
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{args.base_url.rstrip('/')}/audit/evidence/export", headers=headers)
        response.raise_for_status()
    args.output.write_bytes(response.content)
    print(f"Wrote evidence pack to {args.output}")


if __name__ == "__main__":
    main()
