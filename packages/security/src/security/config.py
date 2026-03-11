from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from security.secrets import resolve_secret


def resolve_config(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {key: resolve_config(item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_config(item) for item in value]
    if isinstance(value, str):
        return resolve_secret(value)
    return value


def load_yaml(path: Path) -> Any:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return resolve_config(data)
