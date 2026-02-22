from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path

import yaml
from template_models import CanonicalTemplateDefinition, CanonicalTemplateSummary, TemplateType

ROOT = Path(__file__).resolve().parents[3]
INDEX_PATH = ROOT / "docs" / "templates" / "index.json"
LEGACY_MAP_PATH = ROOT / "docs" / "templates" / "migration" / "legacy-to-canonical.csv"


@lru_cache(maxsize=1)
def _load_index() -> list[dict[str, object]]:
    with INDEX_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [item for item in payload.get("templates", []) if isinstance(item, dict)]


@lru_cache(maxsize=1)
def _legacy_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    by_path = {str(item.get("path")): str(item.get("template_id")) for item in _load_index()}
    with LEGACY_MAP_PATH.open("r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            old_path = (row.get("old_path") or "").strip().strip('"')
            new_path = (row.get("new_path") or "").split(" ", 1)[0].strip().strip('"')
            canonical_id = by_path.get(new_path)
            if not canonical_id:
                continue
            keys = {
                old_path,
                Path(old_path).name,
                Path(old_path).stem,
                Path(old_path).stem.replace("_", "-"),
            }
            for key in list(keys):
                if key.endswith("-template"):
                    keys.add(key[: -len("-template")])
                if key.endswith("-example"):
                    keys.add(key[: -len("-example")])
            for key in keys:
                if key:
                    aliases[key.lower()] = canonical_id

    # Allow short IDs where unique (e.g. project-charter -> project-charter.universal.v1).
    short_ids: dict[str, str] = {}
    duplicate_short_ids: set[str] = set()
    for item in _load_index():
        canonical_id = str(item.get("template_id", ""))
        short_id = canonical_id.split(".", 1)[0]
        if short_id in short_ids and short_ids[short_id] != canonical_id:
            duplicate_short_ids.add(short_id)
            continue
        short_ids[short_id] = canonical_id
    for short_id, canonical_id in short_ids.items():
        if short_id not in duplicate_short_ids:
            aliases[short_id.lower()] = canonical_id
    return aliases


def _resolve_id(template_id: str) -> str:
    lowered = template_id.lower()
    if lowered in _legacy_aliases():
        return _legacy_aliases()[lowered]
    return template_id


def _manifest_metadata(path_value: str) -> tuple[str, str]:
    manifest_path = ROOT / path_value
    if not manifest_path.exists():
        return "", ""
    with manifest_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    metadata = payload.get("metadata") if isinstance(payload, dict) else {}
    guidance = payload.get("guidance") if isinstance(payload, dict) else {}
    title = metadata.get("title") if isinstance(metadata, dict) else ""
    purpose = guidance.get("purpose") if isinstance(guidance, dict) else ""
    return str(title or ""), str(purpose or "")


def _entry_to_model(entry: dict[str, object]) -> CanonicalTemplateDefinition:
    canonical_id = str(entry.get("template_id", ""))
    path_value = str(entry.get("path", ""))
    title, purpose = _manifest_metadata(path_value)
    artefact_type = str(entry.get("artefact_type", ""))
    template_type = (
        TemplateType.spreadsheet
        if artefact_type in {"dashboard", "backlog"}
        else TemplateType.document
    )

    legacy_ids = sorted([k for k, v in _legacy_aliases().items() if v == canonical_id])
    return CanonicalTemplateDefinition(
        template_id=canonical_id,
        canonical_template_id=canonical_id,
        name=title or canonical_id,
        description=purpose or f"Canonical {artefact_type} template",
        type=template_type,
        tags=sorted({artefact_type, str(entry.get("methodology", ""))}),
        artefact_type=artefact_type,
        methodology=str(entry.get("methodology", "")),
        compliance_tags=[
            str(item) for item in entry.get("compliance_tags", []) if isinstance(item, str)
        ],
        version=str(entry.get("version", "")),
        status=str(entry.get("status", "")),
        supports_modular=bool(entry.get("supports_modular", False)),
        path=path_value,
        required_fields=[
            str(item) for item in entry.get("required_fields", []) if isinstance(item, str)
        ],
        replaces=str(entry.get("replaces")) if entry.get("replaces") else None,
        placeholder_schema_ref=(
            str(entry.get("placeholder_schema_ref"))
            if entry.get("placeholder_schema_ref")
            else None
        ),
        legacy_ids=legacy_ids,
    )


def list_catalog_templates(
    *,
    artefact: str | None = None,
    methodology: str | None = None,
    compliance_tag: str | None = None,
    query: str | None = None,
) -> list[CanonicalTemplateSummary]:
    results = [_entry_to_model(item) for item in _load_index()]
    if artefact:
        expected = artefact.strip().lower()
        results = [item for item in results if item.artefact_type.lower() == expected]
    if methodology:
        expected = methodology.strip().lower()
        results = [item for item in results if item.methodology.lower() == expected]
    if compliance_tag:
        expected = compliance_tag.strip().lower()
        results = [
            item for item in results if any(tag.lower() == expected for tag in item.compliance_tags)
        ]
    if query:
        needle = query.strip().lower()
        results = [
            item
            for item in results
            if needle in item.name.lower()
            or needle in item.description.lower()
            or needle in item.template_id.lower()
            or any(needle in tag.lower() for tag in item.tags)
        ]
    return [
        CanonicalTemplateSummary.model_validate(
            item.model_dump(exclude={"required_fields", "replaces", "placeholder_schema_ref"})
        )
        for item in results
    ]


def get_catalog_template(template_id: str) -> CanonicalTemplateDefinition | None:
    resolved_id = _resolve_id(template_id)
    entry = next(
        (item for item in _load_index() if str(item.get("template_id", "")) == resolved_id),
        None,
    )
    if not entry:
        return None
    return _entry_to_model(entry)
