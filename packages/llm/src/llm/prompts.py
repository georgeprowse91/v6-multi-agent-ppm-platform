from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from jinja2 import Environment, StrictUndefined, meta

EnvironmentTag = Literal["dev", "staging", "prod"]


@dataclass(frozen=True)
class PromptMetadata:
    owner: str
    created_by: str
    status: str = "draft"
    experiment_tags: list[str] = field(default_factory=list)
    defaults: dict[str, Any] = field(default_factory=dict)
    required_variables: list[str] = field(default_factory=list)
    flagged: bool = False
    flagged_reason: str | None = None


@dataclass(frozen=True)
class PromptVersion:
    name: str
    version: int
    version_label: str
    content: str
    status: str
    environment_tags: list[EnvironmentTag]
    metadata: PromptMetadata
    created_at: str
    supersedes_version: int | None = None


class PromptRegistry:
    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or Path(
            os.getenv("PROMPT_REGISTRY_PATH", "data/prompts/registry.json")
        )
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._save({"prompts": {}, "evaluations": []})

    def list_prompts(self, *, environment: EnvironmentTag | None = None) -> list[PromptVersion]:
        data = self._load()
        prompts: list[PromptVersion] = []
        for versions in data.get("prompts", {}).values():
            for version in versions:
                prompt_version = self._to_prompt_version(version)
                if environment and environment not in prompt_version.environment_tags:
                    continue
                prompts.append(prompt_version)
        return sorted(prompts, key=lambda item: (item.name, item.version))

    def get_prompt(
        self,
        name: str,
        *,
        version: int | None = None,
        environment: EnvironmentTag | None = None,
    ) -> PromptVersion:
        versions = self._load().get("prompts", {}).get(name, [])
        candidates = [self._to_prompt_version(item) for item in versions]
        if version is not None:
            for candidate in candidates:
                if candidate.version == version:
                    if environment and environment not in candidate.environment_tags:
                        raise KeyError("Prompt version not scoped to requested environment")
                    return candidate
            raise KeyError("Prompt version not found")

        filtered = [
            c for c in candidates if environment is None or environment in c.environment_tags
        ]
        if not filtered:
            raise KeyError("Prompt not found")
        return max(filtered, key=lambda item: item.version)

    def register_prompt(
        self,
        name: str,
        content: str,
        *,
        owner: str = "unknown",
        created_by: str = "system",
        status: str = "draft",
        experiment_tags: list[str] | None = None,
        defaults: dict[str, Any] | None = None,
        required_variables: list[str] | None = None,
        environment_tags: list[EnvironmentTag] | None = None,
        version_label: str | None = None,
    ) -> PromptVersion:
        data = self._load()
        versions = data.setdefault("prompts", {}).setdefault(name, [])
        version_number = max([entry["version"] for entry in versions], default=0) + 1
        record = PromptVersion(
            name=name,
            version=version_number,
            version_label=version_label or f"v{version_number}",
            content=content,
            status=status,
            environment_tags=environment_tags or ["dev"],
            metadata=PromptMetadata(
                owner=owner,
                created_by=created_by,
                status=status,
                experiment_tags=experiment_tags or [],
                defaults=defaults or {},
                required_variables=required_variables or [],
            ),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        versions.append(self._serialise_prompt(record))
        self._save(data)
        return record

    def update_prompt(
        self, name: str, *, content: str | None = None, **kwargs: Any
    ) -> PromptVersion:
        latest = self.get_prompt(name)
        metadata = asdict(latest.metadata)
        metadata.update({k: v for k, v in kwargs.items() if k in metadata and v is not None})
        return self.register_prompt(
            name=name,
            content=content or latest.content,
            owner=metadata["owner"],
            created_by=metadata["created_by"],
            status=kwargs.get("status", latest.status),
            experiment_tags=metadata["experiment_tags"],
            defaults=metadata["defaults"],
            required_variables=metadata["required_variables"],
            environment_tags=kwargs.get("environment_tags", latest.environment_tags),
            version_label=kwargs.get("version_label"),
        )

    def promote_prompt(self, name: str, version: int, environment: EnvironmentTag) -> PromptVersion:
        source = self.get_prompt(name, version=version)
        tags = sorted(set([*source.environment_tags, environment]))
        return self.update_prompt(
            name,
            content=source.content,
            status="promoted",
            environment_tags=tags,
            version_label=f"{source.version_label}-{environment}",
        )

    def delete_prompt(self, name: str, *, actor: str = "system") -> PromptVersion:
        latest = self.get_prompt(name)
        return self.update_prompt(name, status="deleted", created_by=actor, content=latest.content)

    def flag_prompt_version(self, name: str, version: int, reason: str) -> PromptVersion:
        data = self._load()
        versions = data.get("prompts", {}).get(name, [])
        for idx, item in enumerate(versions):
            if item["version"] == version:
                item["metadata"]["flagged"] = True
                item["metadata"]["flagged_reason"] = reason
                versions[idx] = item
                self._save(data)
                return self._to_prompt_version(item)
        raise KeyError("Prompt version not found")

    def list_flagged_prompts(self) -> list[PromptVersion]:
        return [p for p in self.list_prompts() if p.metadata.flagged]

    def render_prompt(
        self, name: str, variables: dict[str, Any], *, version: int | None = None
    ) -> str:
        prompt = self.get_prompt(name, version=version)
        payload = {**prompt.metadata.defaults, **variables}
        required = set(prompt.metadata.required_variables)
        missing_required = [item for item in required if item not in payload]
        if missing_required:
            raise ValueError(f"Missing required variables: {missing_required}")

        environment = Environment(undefined=StrictUndefined, autoescape=False)
        parsed = environment.parse(prompt.content)
        template_vars = meta.find_undeclared_variables(parsed)
        missing = [item for item in template_vars if item not in payload]
        if missing:
            raise ValueError(f"Missing template variables: {sorted(missing)}")

        return environment.from_string(prompt.content).render(**payload)

    def append_evaluation_record(self, record: dict[str, Any]) -> None:
        data = self._load()
        data.setdefault("evaluations", []).append(record)
        self._save(data)

    def _to_prompt_version(self, payload: dict[str, Any]) -> PromptVersion:
        return PromptVersion(
            name=payload["name"],
            version=payload["version"],
            version_label=payload.get("version_label", f"v{payload['version']}"),
            content=payload["content"],
            status=payload.get("status", "draft"),
            environment_tags=payload.get("environment_tags", ["dev"]),
            metadata=PromptMetadata(**payload.get("metadata", {})),
            created_at=payload["created_at"],
            supersedes_version=payload.get("supersedes_version"),
        )

    def _serialise_prompt(self, prompt: PromptVersion) -> dict[str, Any]:
        payload = asdict(prompt)
        payload["metadata"] = asdict(prompt.metadata)
        return payload

    def _load(self) -> dict[str, Any]:
        return dict(json.loads(self.registry_path.read_text()))

    def _save(self, payload: dict[str, Any]) -> None:
        self.registry_path.write_text(json.dumps(payload, indent=2))
