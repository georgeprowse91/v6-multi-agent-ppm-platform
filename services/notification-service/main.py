from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

import main as service_main  # noqa: E402

app = service_main.app


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)
