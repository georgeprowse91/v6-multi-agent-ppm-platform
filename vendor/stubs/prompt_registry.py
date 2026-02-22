from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REDACTION_KEYS = {"password", "secret", "token", "api_key", "ssn"}
_VERSION_RE = re.compile(r"_v(?P<version>\d+)\.md$")


@dataclass(frozen=True)
class PromptRecord:
    agent_id: str
    version: int
    path: Path
    description: str
    content: str


class PromptRegistry:
    def __init__(self, prompts_root: Path | None = None) -> None:
        self.prompts_root = prompts_root or (Path(__file__).resolve().parents[2] / "agents" / "runtime" / "prompts")
        self._prompt_cache: dict[tuple[str, int], PromptRecord] = {}
        self._agent_versions: dict[str, list[int]] = {}

    def get_prompt(self, agent_id: str, version: int | None = None) -> str:
        return self.get_prompt_record(agent_id, version).content

    def get_prompt_record(self, agent_id: str, version: int | None = None) -> PromptRecord:
        version_to_use = version or self.latest_version(agent_id)
        cache_key = (agent_id, version_to_use)
        if cache_key not in self._prompt_cache:
            path = self._find_prompt_path(agent_id, version_to_use)
            self._prompt_cache[cache_key] = self._load_prompt_file(agent_id, version_to_use, path)
        return self._prompt_cache[cache_key]

    def latest_version(self, agent_id: str) -> int:
        versions = self._list_versions(agent_id)
        if not versions:
            raise ValueError(f"No prompt versions found for agent '{agent_id}'")
        return max(versions)

    def next_version(self, agent_id: str) -> int:
        versions = self._list_versions(agent_id)
        return (max(versions) + 1) if versions else 1

    def _list_versions(self, agent_id: str) -> list[int]:
        if agent_id in self._agent_versions:
            return self._agent_versions[agent_id]
        agent_dir = self.prompts_root / agent_id
        if not agent_dir.exists():
            self._agent_versions[agent_id] = []
            return []
        versions: list[int] = []
        for file_path in agent_dir.glob("*.md"):
            match = _VERSION_RE.search(file_path.name)
            if match:
                versions.append(int(match.group("version")))
        versions.sort()
        self._agent_versions[agent_id] = versions
        return versions

    def _find_prompt_path(self, agent_id: str, version: int) -> Path:
        agent_dir = self.prompts_root / agent_id
        if not agent_dir.exists():
            raise ValueError(f"Prompt directory not found for agent '{agent_id}'")
        for file_path in sorted(agent_dir.glob("*.md")):
            match = _VERSION_RE.search(file_path.name)
            if match and int(match.group("version")) == version:
                return file_path
        raise ValueError(f"Prompt version '{version}' not found for agent '{agent_id}'")

    def _load_prompt_file(self, agent_id: str, version: int, path: Path) -> PromptRecord:
        raw = path.read_text(encoding="utf-8")
        metadata, content = self._split_metadata(raw)
        file_version = int(metadata.get("version", version))
        if file_version != version:
            raise ValueError(
                f"Prompt metadata version mismatch for {path}: expected {version}, found {file_version}"
            )
        description = str(metadata.get("description", "")).strip()
        return PromptRecord(
            agent_id=agent_id,
            version=file_version,
            path=path,
            description=description,
            content=content.strip(),
        )

    @staticmethod
    def _split_metadata(raw: str) -> tuple[dict[str, str], str]:
        metadata: dict[str, str] = {}
        lines = raw.splitlines()
        split_index = 0
        for idx, line in enumerate(lines):
            if line.strip() == "---":
                split_index = idx + 1
                break
            if not line.strip():
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        content = "\n".join(lines[split_index:]) if split_index else raw
        return metadata, content


def _redact_value(value: Any, strategy: str) -> Any:
    if strategy == "drop":
        return None
    return "[REDACTED]"


def _apply_redaction(
    payload: dict[str, Any],
    fields: set[str],
    strategy: str,
) -> dict[str, Any]:
    def match_key(mapping: dict[str, Any], part: str) -> str | None:
        if part in mapping:
            return part
        lowered = part.lower()
        if lowered in REDACTION_KEYS:
            for key in mapping:
                if key.lower() == lowered:
                    return key
        return None

    def apply_path(target: Any, parts: list[str]) -> None:
        if not parts:
            return
        if isinstance(target, list):
            for item in target:
                apply_path(item, parts)
            return
        if not isinstance(target, dict):
            return
        key = match_key(target, parts[0])
        if key is None:
            return
        if len(parts) == 1:
            target[key] = _redact_value(target[key], strategy)
            return
        apply_path(target[key], parts[1:])

    redacted = dict(payload)
    for field in fields:
        apply_path(redacted, field.split("."))
    return redacted


def enforce_redaction(payload: dict[str, Any]) -> dict[str, Any]:
    fields = {"user.email", "user.phone", "user.ssn"}
    fields.update({f"secrets.{key}" for key in REDACTION_KEYS})
    return _apply_redaction(payload, fields, strategy="mask")
