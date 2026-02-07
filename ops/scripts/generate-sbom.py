#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


def main() -> int:
    output_path = Path(os.getenv("SBOM_OUTPUT", "dist/sbom.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    packages = []
    for dist in metadata.distributions():
        packages.append(
            {
                "name": dist.metadata["Name"],
                "version": dist.version,
            }
        )

    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "multi-agent-ppm-platform",
        "documentNamespace": f"urn:ppm:sbom:{datetime.now(timezone.utc).isoformat()}",
        "creationInfo": {
            "created": datetime.now(timezone.utc).isoformat(),
            "creators": ["Tool: generate-sbom.py"],
        },
        "packages": [
            {
                "SPDXID": f"SPDXRef-Package-{pkg['name']}",
                "name": pkg["name"],
                "versionInfo": pkg["version"],
            }
            for pkg in sorted(packages, key=lambda x: x["name"].lower())
        ],
    }

    output_path.write_text(json.dumps(sbom, indent=2))
    print(f"SBOM written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
