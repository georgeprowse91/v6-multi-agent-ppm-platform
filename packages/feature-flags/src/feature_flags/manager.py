from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from security.config import load_yaml


@dataclass(frozen=True)
class FeatureFlag:
    name: str
    enabled: bool
    description: str | None = None


MCP_GLOBAL_FLAG = "mcp_global_enabled"
MCP_SYSTEM_PREFIX = "mcp_system_"
MCP_PROJECT_PREFIX = "mcp_project_"


_DEPENDENCY_DEGRADED: set[str] = set()


def set_dependency_degraded(dependency: str) -> None:
    _DEPENDENCY_DEGRADED.add(_normalize_flag_key(dependency))


def clear_dependency_degraded(dependency: str) -> None:
    _DEPENDENCY_DEGRADED.discard(_normalize_flag_key(dependency))


def is_dependency_degraded(dependency: str) -> bool:
    return _normalize_flag_key(dependency) in _DEPENDENCY_DEGRADED


def should_use_degraded_mode(
    feature: str, dependency: str, *, environment: str | None = None
) -> bool:
    if is_feature_enabled(feature, environment=environment, default=False):
        return True
    return is_dependency_degraded(dependency)


def _normalize_flag_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


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


def get_flag_state(name: str, *, environment: str | None = None) -> bool | None:
    flags = load_feature_flags(environment)
    if name not in flags:
        return None
    return flags[name].enabled


def mcp_system_flag(system: str) -> str:
    return f"{MCP_SYSTEM_PREFIX}{_normalize_flag_key(system)}"


def mcp_project_flag(project_id: str) -> str:
    return f"{MCP_PROJECT_PREFIX}{_normalize_flag_key(project_id)}"


def is_mcp_feature_enabled(
    system: str | None = None,
    *,
    project_id: str | None = None,
    environment: str | None = None,
    default: bool = False,
) -> bool:
    resolved_environment = environment or os.getenv("ENVIRONMENT") or None

    if project_id:
        project_flag = get_flag_state(
            mcp_project_flag(project_id), environment=resolved_environment
        )
        if project_flag is not None:
            return project_flag

    if system:
        system_flag = get_flag_state(mcp_system_flag(system), environment=resolved_environment)
        if system_flag is not None:
            return system_flag

    global_flag = get_flag_state(MCP_GLOBAL_FLAG, environment=resolved_environment)
    if global_flag is not None:
        return global_flag
    return default


def is_feature_enabled(name: str, *, environment: str | None = None, default: bool = False) -> bool:
    flags = load_feature_flags(environment)
    if name not in flags:
        return default
    return flags[name].enabled


def clear_all_dependency_degraded() -> None:
    _DEPENDENCY_DEGRADED.clear()
