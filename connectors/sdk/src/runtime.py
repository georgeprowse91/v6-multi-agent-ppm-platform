from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from connectors.sdk.src.classification import infer_classification
from connectors.sdk.src.data_service_client import (
    DataLineageClient,
    DataServiceClient,
    LineageEventEmitter,
)
from connectors.sdk.src.quality import evaluate_quality
from connectors.sdk.src.transformations import apply_transformation
from connectors.sdk.src.telemetry import get_connector_telemetry


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
    maturity: dict[str, Any]


@dataclass
class MappingSpec:
    source: str
    target: str
    fields: list[dict[str, Any]]
    schema: str | None = None
    transformations: list[dict[str, Any]] | None = None


class ConnectorRuntime:
    def __init__(self, connector_root: Path) -> None:
        self.connector_root = connector_root
        self.manifest = self._load_manifest(connector_root / "manifest.yaml")
        self.telemetry = get_connector_telemetry(self.manifest.id)

    def _load_manifest(self, path: Path) -> ConnectorManifest:
        data = yaml.safe_load(path.read_text())
        schema_path = (
            Path(__file__).resolve().parents[4]
            / "integrations"
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
        schema_path = (
            Path(__file__).resolve().parents[4]
            / "integrations"
            / "connectors"
            / "registry"
            / "schemas"
            / "connector-mapping.schema.json"
        )
        schema = yaml.safe_load(schema_path.read_text())
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(data), key=lambda err: err.path)
        if errors:
            formatted = "; ".join(error.message for error in errors)
            raise ValueError(f"Connector mapping validation failed ({path}): {formatted}")
        return MappingSpec(
            source=data["source"],
            target=data["target"],
            fields=data.get("fields", []),
            schema=data.get("schema") or data.get("target"),
            transformations=data.get("transformations"),
        )

    def _apply_mapping(self, record: dict[str, Any], mapping: MappingSpec, tenant_id: str) -> dict[str, Any]:
        mapped: dict[str, Any] = {"tenant_id": tenant_id}
        for entry in mapping.fields:
            source_field = entry.get("source")
            target_field = entry.get("target")
            if not source_field or not target_field:
                continue
            value = record.get(source_field)
            value = apply_transformation(value, entry.get("transform"))
            mapped[target_field] = value
        if mapping.transformations:
            for transform in mapping.transformations:
                field = transform.get("field")
                if not field:
                    continue
                mapped[field] = apply_transformation(mapped.get(field), transform)
        return mapped

    def apply_mappings(
        self,
        records: list[dict[str, Any]],
        tenant_id: str,
        include_schema: bool = False,
        *,
        emit_lineage: bool = True,
    ) -> list[dict[str, Any]]:
        attributes = {
            "connector_version": self.manifest.version,
            "connector_name": self.manifest.name,
            "tenant_id": tenant_id,
        }
        with self.telemetry.track_sync("apply_mappings", attributes) as span_attributes:
            results: list[dict[str, Any]] = []
            mapping_specs = [
                self._load_mapping(self.connector_root / mapping["mapping_file"])
                for mapping in self.manifest.mappings
            ]
            emitter = self._get_lineage_emitter(tenant_id) if emit_lineage else None
            for record in records:
                for spec in mapping_specs:
                    if record.get("source") and record.get("source") != spec.source:
                        continue
                    mapped = self._apply_mapping(record, spec, tenant_id)
                    if include_schema:
                        mapped["schema_name"] = spec.schema or spec.target
                    results.append(mapped)
                    quality = None
                    if spec.schema or spec.target:
                        quality = evaluate_quality(spec.schema or spec.target, mapped)
                    classification = infer_classification(record, mapped)
                    if emitter:
                        emitter.emit_event(
                            source=self._source_entity(record, spec),
                            target=self._target_entity(mapped, spec),
                            transformations=self._transformation_steps(spec),
                            entity_type=spec.schema or spec.target,
                            entity_payload=mapped,
                            quality=quality,
                            classification=classification,
                            metadata={
                                "connector_version": self.manifest.version,
                                "mapping_source": spec.source,
                                "mapping_target": spec.target,
                            },
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
            if emitter:
                emitter.client.close()
            self.telemetry.record_records(len(results), span_attributes)
            return results

    def run_sync(
        self,
        fixture_path: Path,
        tenant_id: str,
        include_schema: bool = False,
        *,
        emit_lineage: bool = True,
    ) -> list[dict[str, Any]]:
        raw = json.loads(fixture_path.read_text())
        if not isinstance(raw, list):
            raise ValueError("Fixture must be a list of records")
        return self.apply_mappings(
            raw,
            tenant_id,
            include_schema=include_schema,
            emit_lineage=emit_lineage,
        )

    def store_canonical_entities(
        self,
        entities: list[dict[str, Any]],
        schema_name: str,
        data_service: DataServiceClient,
    ) -> list[dict[str, Any]]:
        stored: list[dict[str, Any]] = []
        for entity in entities:
            stored.append(
                data_service.store_entity(
                    schema_name,
                    entity,
                    entity_id=entity.get("id"),
                )
            )
        return stored

    def _get_lineage_emitter(self, tenant_id: str) -> LineageEventEmitter | None:
        base_url = os.getenv("DATA_LINEAGE_SERVICE_URL")
        if not base_url:
            return None
        client = DataLineageClient.from_url(base_url, tenant_id)
        return LineageEventEmitter(self.manifest.id, client=client)

    def _source_entity(self, record: dict[str, Any], spec: MappingSpec) -> dict[str, Any]:
        return {
            "system": self.manifest.id,
            "entity": spec.source,
            "record_id": record.get("id"),
        }

    def _target_entity(self, mapped: dict[str, Any], spec: MappingSpec) -> dict[str, Any]:
        return {
            "schema": spec.schema or spec.target,
            "record_id": mapped.get("id"),
        }

    def _transformation_steps(self, spec: MappingSpec) -> list[str]:
        steps: list[str] = []
        for entry in spec.fields:
            source_field = entry.get("source")
            target_field = entry.get("target")
            if source_field and target_field:
                transform = entry.get("transform")
                if transform:
                    steps.append(
                        f"map {source_field} -> {target_field} ({transform.get('type', 'transform')})"
                    )
                else:
                    steps.append(f"map {source_field} -> {target_field}")
        if spec.transformations:
            for transform in spec.transformations:
                if transform.get("field"):
                    steps.append(
                        f"transform {transform.get('field')} ({transform.get('type', 'transform')})"
                    )
        return steps
