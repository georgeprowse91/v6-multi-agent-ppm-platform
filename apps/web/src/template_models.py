from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class TemplateType(StrEnum):
    document = "document"
    spreadsheet = "spreadsheet"


class DocumentTemplateDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: str
    retention_days: int


class DocumentTemplatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_template: str
    content_template: str
    metadata_template: dict[str, Any] | None = None


class SpreadsheetTemplateColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    required: bool = False


class SpreadsheetSeedRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any]


class SpreadsheetTemplatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sheet_name_template: str
    columns: list[SpreadsheetTemplateColumn]
    seed_rows: list[SpreadsheetSeedRow] | None = None


class Template(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    name: str
    type: TemplateType
    description: str
    tags: list[str]
    version: str = "1.0"
    available_versions: list[str] = Field(default_factory=lambda: ["1.0"])
    schema_version: int = 1
    defaults: DocumentTemplateDefaults | None = None
    payload: DocumentTemplatePayload | SpreadsheetTemplatePayload

    def summary(self) -> TemplateSummary:
        return TemplateSummary(
            template_id=self.template_id,
            name=self.name,
            type=self.type,
            description=self.description,
            tags=self.tags,
            version=self.version,
            available_versions=self.available_versions,
            schema_version=self.schema_version,
        )


class TemplateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    name: str
    type: TemplateType
    description: str
    tags: list[str]
    version: str
    available_versions: list[str]
    schema_version: int


class CanonicalTemplateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    canonical_template_id: str
    name: str
    description: str
    type: TemplateType
    tags: list[str]
    artefact_type: str
    methodology: str
    compliance_tags: list[str]
    version: str
    status: str
    supports_modular: bool
    path: str
    legacy_ids: list[str] = Field(default_factory=list)


class CanonicalTemplateDefinition(CanonicalTemplateSummary):
    required_fields: list[str] = Field(default_factory=list)
    replaces: str | None = None
    placeholder_schema_ref: str | None = None


class TemplateInstantiateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    parameters: dict[str, Any] | None = None


class TemplateInstantiateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created_type: TemplateType
    document_id: str | None = None
    sheet_id: str | None = None
    name: str | None = None
    sheet_name: str | None = None
    advisories: list[str] | None = None


def build_placeholder_context(
    *,
    project_id: str,
    tenant_id: str,
    user: str,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = {
        "project_id": project_id,
        "tenant_id": tenant_id,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "user": user,
    }
    if parameters:
        context.update(parameters)
    return context


def substitute_placeholders(value: str, context: dict[str, Any]) -> str:
    rendered, _ = _substitute_placeholders_with_unresolved(value, context)
    return rendered


_PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z_][\w\.]*)\s*}}")


def _resolve_context_key(context: dict[str, Any], key: str) -> Any:
    current: Any = context
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        return None
    return current


def _substitute_placeholders_with_unresolved(
    value: str, context: dict[str, Any]
) -> tuple[str, set[str]]:
    unresolved: set[str] = set()

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        replacement = _resolve_context_key(context, key)
        if replacement is None:
            unresolved.add(key)
            return match.group(0)
        return str(replacement)

    rendered = _PLACEHOLDER_PATTERN.sub(_replace, value)
    return rendered, unresolved


def render_template_value(value: Any, context: dict[str, Any]) -> Any:
    rendered, _ = render_template_value_with_unresolved(value, context)
    return rendered


def render_template_value_with_unresolved(
    value: Any, context: dict[str, Any]
) -> tuple[Any, set[str]]:
    if isinstance(value, str):
        return _substitute_placeholders_with_unresolved(value, context)
    if isinstance(value, list):
        unresolved: set[str] = set()
        rendered = []
        for item in value:
            rendered_item, unresolved_item = render_template_value_with_unresolved(item, context)
            rendered.append(rendered_item)
            unresolved.update(unresolved_item)
        return rendered, unresolved
    if isinstance(value, dict):
        unresolved: set[str] = set()
        rendered: dict[str, Any] = {}
        for key, item in value.items():
            rendered_item, unresolved_item = render_template_value_with_unresolved(item, context)
            rendered[key] = rendered_item
            unresolved.update(unresolved_item)
        return rendered, unresolved
    return value, set()
