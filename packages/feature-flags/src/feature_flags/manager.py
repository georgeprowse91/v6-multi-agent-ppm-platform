from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from security.config import load_yaml


@dataclass(frozen=True)
class FeatureFlag:
    name: str
    enabled: bool
    description: str | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _flags_path() -> Path:
    return _repo_root() / "config" / "feature-flags" / "flags.yaml"


def _environment_path(environment: str) -> Path:
    return _repo_root() / "config" / "environments" / f"{environment}.yaml"


def _load_global_flags() -> dict[str, FeatureFlag]:
    path = _flags_path()
    if not path.exists():
        return {}
    payload = load_yaml(path) or {}
    flags: dict[str, FeatureFlag] = {}
    for entry in payload.get("flags", []):
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name:
            continue
        flags[name] = FeatureFlag(
            name=name,
            enabled=bool(entry.get("enabled", False)),
            description=entry.get("description"),
        )
    return flags


def _load_environment_overrides(environment: str) -> dict[str, bool]:
    path = _environment_path(environment)
    if not path.exists():
        return {}
    payload = load_yaml(path) or {}
    overrides: dict[str, bool] = {}
    for key, value in (payload.get("feature_flags") or {}).items():
        overrides[str(key)] = bool(value)
    return overrides


def load_feature_flags(environment: str | None = None) -> dict[str, FeatureFlag]:
    env_name = environment or "dev"
    flags = _load_global_flags()
    overrides = _load_environment_overrides(env_name)
    for name, enabled in overrides.items():
        if name in flags:
            flags[name] = FeatureFlag(
                name=flags[name].name,
                enabled=enabled,
                description=flags[name].description,
            )
        else:
            flags[name] = FeatureFlag(name=name, enabled=enabled)
    return flags


def is_feature_enabled(name: str, *, environment: str | None = None, default: bool = False) -> bool:
    flags = load_feature_flags(environment)
    if name not in flags:
        return default
    return flags[name].enabled
