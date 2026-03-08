"""Agent manifest definition and validation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "schemas" / "agent-manifest.schema.json"
)


class ManifestAuthor(BaseModel):
    name: str
    email: str | None = None
    url: str | None = None


class ManifestEntryPoint(BaseModel):
    module: str
    class_name: str


class ManifestInput(BaseModel):
    name: str
    type: str
    required: bool = False
    description: str | None = None


class ManifestOutput(BaseModel):
    name: str
    type: str
    description: str | None = None


class ManifestParameter(BaseModel):
    name: str
    display_name: str
    description: str | None = None
    param_type: str = "string"
    default_value: Any = None
    options: list[str] | None = None
    required: bool = False


class ManifestRuntime(BaseModel):
    python_version: str = ">=3.11"
    dependencies: list[str] = Field(default_factory=list)
    memory_mb: int = 256
    timeout_seconds: int = 60
    sandbox: bool = True


class AgentManifest(BaseModel):
    """Pydantic model representing an agent manifest."""

    manifest_version: str = "1.0"
    agent_id: str
    display_name: str
    version: str
    description: str
    long_description: str | None = None
    author: ManifestAuthor | dict[str, str]
    license: str | None = None
    category: str
    tags: list[str] = Field(default_factory=list)
    icon: str | None = None
    entry_point: ManifestEntryPoint | dict[str, str]
    capabilities: list[str]
    inputs: list[ManifestInput] = Field(default_factory=list)
    outputs: list[ManifestOutput] = Field(default_factory=list)
    parameters: list[ManifestParameter] = Field(default_factory=list)
    permissions_required: list[str] = Field(default_factory=list)
    connectors_used: list[str] = Field(default_factory=list)
    schemas_used: list[str] = Field(default_factory=list)
    runtime: ManifestRuntime = Field(default_factory=ManifestRuntime)
    documentation_url: str | None = None
    repository_url: str | None = None
    published_at: str | None = None

    def to_catalog_entry(self) -> dict[str, Any]:
        """Convert manifest to a catalog-compatible entry dict."""
        author = self.author if isinstance(self.author, dict) else self.author.model_dump()
        entry_point = (
            self.entry_point
            if isinstance(self.entry_point, dict)
            else self.entry_point.model_dump()
        )
        return {
            "catalog_id": self.agent_id,
            "agent_id": self.agent_id,
            "component_name": self.agent_id,
            "display_name": self.display_name,
            "version": self.version,
            "description": self.description,
            "long_description": self.long_description,
            "author": author,
            "license": self.license,
            "category": self.category,
            "tags": self.tags,
            "icon": self.icon,
            "entry_point": entry_point,
            "capabilities": self.capabilities,
            "inputs": [i.model_dump() if isinstance(i, BaseModel) else i for i in self.inputs],
            "outputs": [o.model_dump() if isinstance(o, BaseModel) else o for o in self.outputs],
            "parameters": [
                p.model_dump() if isinstance(p, BaseModel) else p for p in self.parameters
            ],
            "permissions_required": self.permissions_required,
            "connectors_used": self.connectors_used,
            "schemas_used": self.schemas_used,
            "runtime": (
                self.runtime.model_dump() if isinstance(self.runtime, BaseModel) else self.runtime
            ),
            "documentation_url": self.documentation_url,
            "repository_url": self.repository_url,
            "published_at": self.published_at,
            "source": "marketplace",
        }


def validate_manifest(manifest_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a manifest dict against the agent-manifest JSON schema.

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    errors: list[str] = []

    try:
        from jsonschema import Draft202012Validator

        if _SCHEMA_PATH.exists():
            schema = json.loads(_SCHEMA_PATH.read_text())
            validator = Draft202012Validator(schema)
            for error in validator.iter_errors(manifest_data):
                errors.append(f"{error.json_path}: {error.message}")
        else:
            # Fallback: validate via Pydantic only
            AgentManifest.model_validate(manifest_data)
    except ImportError:
        # jsonschema not available, use Pydantic validation
        try:
            AgentManifest.model_validate(manifest_data)
        except Exception as exc:
            errors.append(str(exc))
    except Exception as exc:
        errors.append(str(exc))

    return (len(errors) == 0, errors)


def load_manifest_from_file(path: str | Path) -> AgentManifest:
    """Load and validate an agent manifest from a JSON file."""
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"Manifest file not found: {filepath}")
    data = json.loads(filepath.read_text())
    is_valid, errors = validate_manifest(data)
    if not is_valid:
        raise ValueError(f"Invalid manifest: {'; '.join(errors)}")
    return AgentManifest.model_validate(data)
