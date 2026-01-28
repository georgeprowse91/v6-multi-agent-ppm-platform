from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict

SpreadsheetColumnType = Literal["text", "number", "date", "bool"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _strip_required(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("value must be non-empty")
    return trimmed


class ColumnCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    type: SpreadsheetColumnType
    required: bool = False

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _strip_required(value)


class Column(ColumnCreate):
    column_id: str

    @classmethod
    def build(cls, payload: ColumnCreate) -> "Column":
        return cls(
            column_id=str(uuid4()),
            name=payload.name,
            type=payload.type,
            required=payload.required,
        )


class SheetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    columns: list[ColumnCreate]

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _strip_required(value)

    @field_validator("columns")
    @classmethod
    def _validate_columns(cls, value: list[ColumnCreate]) -> list[ColumnCreate]:
        names = [column.name.strip().lower() for column in value]
        if len(names) != len(set(names)):
            raise ValueError("column names must be unique")
        return value


class Sheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sheet_id: str
    tenant_id: str
    project_id: str
    name: str
    columns: list[Column]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def build(cls, tenant_id: str, project_id: str, payload: SheetCreate) -> "Sheet":
        now = utc_now()
        columns = [Column.build(column) for column in payload.columns]
        return cls(
            sheet_id=str(uuid4()),
            tenant_id=tenant_id,
            project_id=project_id,
            name=payload.name,
            columns=columns,
            created_at=now,
            updated_at=now,
        )


class RowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any]


class RowUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any]


class Row(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_id: str
    values: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def build(cls, payload: dict[str, Any]) -> "Row":
        now = utc_now()
        return cls(
            row_id=str(uuid4()),
            values=payload,
            created_at=now,
            updated_at=now,
        )


class SheetDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sheet: Sheet
    rows: list[Row]


class ImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    imported: int


class DeleteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deleted: bool
    row_id: str


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def coerce_value(column: Column, value: Any) -> Any:
    if value is None:
        return None
    if column.type == "text":
        if isinstance(value, str):
            return value
        return str(value)
    if column.type == "number":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            return float(value)
        raise ValueError("number columns must be numeric")
    if column.type == "date":
        if isinstance(value, str):
            try:
                parsed = datetime.strptime(value, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError("date must be YYYY-MM-DD") from exc
            return parsed.strftime("%Y-%m-%d")
        raise ValueError("date must be YYYY-MM-DD")
    if column.type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "false"}:
                return lowered == "true"
        raise ValueError("bool must be true or false")
    raise ValueError("Unsupported column type")


def validate_row_values(
    columns: list[Column],
    values: dict[str, Any],
    *,
    require_all: bool,
) -> dict[str, Any]:
    column_map = {column.column_id: column for column in columns}
    for column_id in values:
        if column_id not in column_map:
            raise ValueError(f"Unknown column_id: {column_id}")

    normalized: dict[str, Any] = {}
    for column in columns:
        if column.column_id not in values:
            if require_all and column.required:
                raise ValueError(f"Missing required column: {column.name}")
            continue

        raw_value = values[column.column_id]
        if _is_empty(raw_value):
            if column.required:
                raise ValueError(f"Column '{column.name}' is required")
            normalized[column.column_id] = None
            continue

        normalized[column.column_id] = coerce_value(column, raw_value)

    if require_all:
        for column in columns:
            if column.required and column.column_id not in normalized:
                raise ValueError(f"Column '{column.name}' is required")

    return normalized
