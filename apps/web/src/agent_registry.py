from __future__ import annotations

import importlib.util
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from agent_settings_models import AgentRegistryEntry

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CATALOG_PATH = REPO_ROOT / "agents" / "runtime" / "src" / "agent_catalog.py"
DOC_CATALOG_PATH = REPO_ROOT / "docs" / "agents" / "agent-catalog.md"

REQUIRED_AGENT_IDS = {"intent-router", "response-orchestration"}


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _load_runtime_catalog() -> list[dict[str, Any]]:
    if not RUNTIME_CATALOG_PATH.exists():
        return []
    spec = importlib.util.spec_from_file_location("agent_catalog", RUNTIME_CATALOG_PATH)
    if not spec or not spec.loader:
        return []
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    entries = getattr(module, "AGENT_CATALOG", ())
    result = []
    for entry in entries:
        result.append(
            {
                "agent_id": entry.agent_id,
                "name": entry.display_name,
            }
        )
    return result


def _parse_doc_catalog() -> dict[str, dict[str, Any]]:
    if not DOC_CATALOG_PATH.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    lines = DOC_CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    for line in lines:
        if not line.lstrip().startswith("| **Agent"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) < 4:
            continue
        agent_cell = parts[0]
        match = re.search(r"Agent\s+\d+\s+–\s+(.+)", agent_cell)
        if not match:
            continue
        name = match.group(1).replace("**", "").strip()
        purpose = parts[1].strip()
        outputs = parts[3].strip()
        rows[_normalize_name(name)] = {
            "description": purpose or "Not found in repo evidence",
            "outputs": _split_outputs(outputs),
        }
    return rows


def _split_outputs(value: str) -> list[str]:
    if not value:
        return []
    cleaned = value.replace(".", "").strip()
    if not cleaned:
        return []
    return [part.strip() for part in cleaned.split(",") if part.strip()]


@lru_cache(maxsize=1)
def load_agent_registry() -> list[AgentRegistryEntry]:
    runtime_entries = _load_runtime_catalog()
    doc_entries = _parse_doc_catalog()
    if runtime_entries:
        registry = []
        for entry in runtime_entries:
            name = entry["name"]
            doc = doc_entries.get(_normalize_name(name), {})
            registry.append(
                AgentRegistryEntry(
                    agent_id=entry["agent_id"],
                    name=name,
                    category="Not found in repo evidence",
                    description=doc.get("description") or "Not found in repo evidence",
                    outputs=doc.get("outputs", []),
                    default_enabled=True,
                    required=entry["agent_id"] in REQUIRED_AGENT_IDS,
                )
            )
        return registry

    registry = []
    for name_key, doc in doc_entries.items():
        registry.append(
            AgentRegistryEntry(
                agent_id=name_key.replace(" ", "-"),
                name=name_key.title(),
                category="Not found in repo evidence",
                description=doc.get("description") or "Not found in repo evidence",
                outputs=doc.get("outputs", []),
                default_enabled=True,
                required=False,
            )
        )
    return registry
