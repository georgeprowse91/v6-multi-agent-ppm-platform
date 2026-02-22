from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelRecord:
    provider: str
    model_id: str
    display_name: str
    enabled: bool
    capabilities: tuple[str, ...]
    allow_in_demo: bool


class ModelRegistryError(ValueError):
    pass


def _registry_path() -> Path:
    custom = os.getenv("LLM_MODEL_REGISTRY_PATH")
    if custom:
        return Path(custom)
    return Path(__file__).resolve().parents[3] / "apps" / "web" / "data" / "llm_models.json"


def _validate_entry(entry: dict[str, Any], idx: int) -> ModelRecord:
    required = ["provider", "model_id", "display_name", "enabled", "capabilities", "allow_in_demo"]
    missing = [field for field in required if field not in entry]
    if missing:
        raise ModelRegistryError(f"Model index={idx} missing fields: {', '.join(missing)}")
    capabilities = entry.get("capabilities")
    if not isinstance(capabilities, list) or not all(
        isinstance(item, str) for item in capabilities
    ):
        raise ModelRegistryError(f"Model index={idx} capabilities must be a list[str]")
    return ModelRecord(
        provider=str(entry["provider"]).lower(),
        model_id=str(entry["model_id"]),
        display_name=str(entry["display_name"]),
        enabled=bool(entry["enabled"]),
        capabilities=tuple(capabilities),
        allow_in_demo=bool(entry["allow_in_demo"]),
    )


@lru_cache(maxsize=1)
def load_model_registry() -> list[ModelRecord]:
    path = _registry_path()
    if not path.exists():
        raise ModelRegistryError(f"Model registry not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ModelRegistryError("Model registry must be a JSON array")
    return [_validate_entry(item, idx) for idx, item in enumerate(data) if isinstance(item, dict)]


def get_enabled_models(
    *, demo_mode: bool = False, environment: str | None = None
) -> list[ModelRecord]:
    models = [item for item in load_model_registry() if item.enabled]
    if demo_mode:
        models = [item for item in models if item.allow_in_demo]
    env_allowlist = os.getenv("LLM_MODEL_ALLOWLIST", "").strip()
    if env_allowlist:
        allowed = {item.strip() for item in env_allowlist.split(",") if item.strip()}
        models = [item for item in models if f"{item.provider}:{item.model_id}" in allowed]
    provider_allowlist = os.getenv("LLM_PROVIDER_ALLOWLIST", "").strip()
    if provider_allowlist:
        allowed_providers = {
            item.strip().lower() for item in provider_allowlist.split(",") if item.strip()
        }
        models = [item for item in models if item.provider in allowed_providers]
    return models


def find_model(provider: str, model_id: str, *, demo_mode: bool = False) -> ModelRecord | None:
    provider_normalized = (provider or "").lower()
    for item in get_enabled_models(demo_mode=demo_mode):
        if item.provider == provider_normalized and item.model_id == model_id:
            return item
    return None


def clear_model_registry_cache() -> None:
    load_model_registry.cache_clear()
