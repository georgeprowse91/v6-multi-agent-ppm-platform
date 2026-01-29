from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class TemplateType(str, Enum):
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

    def summary(self) -> "TemplateSummary":
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
    rendered = value
    for key, replacement in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(replacement))
    return rendered


def render_template_value(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return substitute_placeholders(value, context)
    if isinstance(value, list):
        return [render_template_value(item, context) for item in value]
    if isinstance(value, dict):
        return {key: render_template_value(item, context) for key, item in value.items()}
    return value
