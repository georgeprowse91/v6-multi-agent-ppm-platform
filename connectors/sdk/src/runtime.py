from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


@dataclass
class ConnectorManifest:
    id: str
    version: str
    name: str
    description: str
    owner: str
    category: str
    auth: dict[str, Any]
    sync: dict[str, Any]
    mappings: list[dict[str, Any]]


@dataclass
class MappingSpec:
    source: str
    target: str
    fields: list[dict[str, str]]


class ConnectorRuntime:
    def __init__(self, connector_root: Path) -> None:
        self.connector_root = connector_root
        self.manifest = self._load_manifest(connector_root / "manifest.yaml")

    def _load_manifest(self, path: Path) -> ConnectorManifest:
        data = yaml.safe_load(path.read_text())
        schema_path = (
            Path(__file__).resolve().parents[3]
            / "connectors"
            / "registry"
            / "schemas"
            / "connector-manifest.schema.json"
        )
        schema = yaml.safe_load(schema_path.read_text())
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(data), key=lambda err: err.path)
        if errors:
            formatted = "; ".join(error.message for error in errors)
            raise ValueError(f"Connector manifest validation failed: {formatted}")
        return ConnectorManifest(**data)

    def _load_mapping(self, path: Path) -> MappingSpec:
        data = yaml.safe_load(path.read_text())
        return MappingSpec(
            source=data["source"],
            target=data["target"],
            fields=data.get("fields", []),
        )

    def _apply_mapping(self, record: dict[str, Any], mapping: MappingSpec, tenant_id: str) -> dict[str, Any]:
        mapped: dict[str, Any] = {"tenant_id": tenant_id}
        for entry in mapping.fields:
            source_field = entry.get("source")
            target_field = entry.get("target")
            if source_field and target_field:
                mapped[target_field] = record.get(source_field)
        return mapped

    def run_sync(self, fixture_path: Path, tenant_id: str) -> list[dict[str, Any]]:
        raw = json.loads(fixture_path.read_text())
        if not isinstance(raw, list):
            raise ValueError("Fixture must be a list of records")
        results: list[dict[str, Any]] = []
        mapping_specs = [
            self._load_mapping(self.connector_root / mapping["mapping_file"])
            for mapping in self.manifest.mappings
        ]
        for record in raw:
            for spec in mapping_specs:
                if record.get("source") and record.get("source") != spec.source:
                    continue
                results.append(self._apply_mapping(record, spec, tenant_id))
        return results
