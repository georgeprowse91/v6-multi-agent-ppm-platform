from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data"


def load_requirements() -> Dict[str, Any]:
    path = data_dir() / "requirements.json"
    if not path.exists():
        return {"functional_domains": [], "non_functional_requirements": []}
    return json.loads(path.read_text(encoding="utf-8"))
