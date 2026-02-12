import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
os.chdir(REPO_ROOT)

pkg_src_dirs = [
    REPO_ROOT / "packages" / d / "src"
    for d in [
        "common", "observability", "security", "llm", "feature-flags",
        "event-bus", "contracts", "data-quality", "workflow", "ui-kit",
    ]
]

paths = [
    str(REPO_ROOT),
    str(REPO_ROOT / "apps" / "web" / "src"),
] + [str(d) for d in pkg_src_dirs if d.exists()]

for p in paths:
    if p not in sys.path:
        sys.path.insert(0, p)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8080,
        reload=False,
        log_level="info",
    )
