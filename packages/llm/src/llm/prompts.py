from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PromptVersion:
    name: str
    version: int
    content: str
    status: str
    updated_at: str


class PromptRegistry:
    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or Path(
            os.getenv("PROMPT_REGISTRY_PATH", "data/prompts/registry.json")
        )
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._save({"prompts": {}})

    def list_prompts(self) -> list[PromptVersion]:
        data = self._load()
        prompts: list[PromptVersion] = []
        for name, versions in data.get("prompts", {}).items():
            for version in versions:
                prompts.append(PromptVersion(**version))
        return sorted(prompts, key=lambda item: (item.name, item.version))

    def register_prompt(self, name: str, content: str) -> PromptVersion:
        data = self._load()
        versions = data.setdefault("prompts", {}).setdefault(name, [])
        version_number = max([entry["version"] for entry in versions], default=0) + 1
        record = PromptVersion(
            name=name,
            version=version_number,
            content=content,
            status="draft",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        versions.append(record.__dict__)
        self._save(data)
        return record

    def promote_prompt(self, name: str, version: int, status: str) -> PromptVersion:
        data = self._load()
        versions = data.get("prompts", {}).get(name, [])
        for entry in versions:
            if entry["version"] == version:
                entry["status"] = status
                entry["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save(data)
                return PromptVersion(**entry)
        raise KeyError("Prompt version not found")

    def _load(self) -> dict[str, Any]:
        return json.loads(self.registry_path.read_text())

    def _save(self, payload: dict[str, Any]) -> None:
        self.registry_path.write_text(json.dumps(payload, indent=2))
