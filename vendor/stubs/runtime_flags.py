from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _load_common_config() -> dict[str, Any]:
    config_path = Path(__file__).resolve().parents[2] / "ops" / "config" / "common.yaml"
    if not config_path.exists():
        return {}
    try:
        content = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return content if isinstance(content, dict) else {}


def demo_mode_enabled() -> bool:
    env_value = os.getenv("DEMO_MODE")
    if env_value is not None:
        return env_value.strip().lower() in _TRUTHY_VALUES

    config_value = _load_common_config().get("DEMO_MODE", False)
    if isinstance(config_value, bool):
        return config_value
    if isinstance(config_value, str):
        return config_value.strip().lower() in _TRUTHY_VALUES
    return bool(config_value)
