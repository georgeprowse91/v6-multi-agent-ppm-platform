from __future__ import annotations

import csv
import json
import os
from io import StringIO
from pathlib import Path
from typing import Any

from spreadsheet_models import (
    Column,
    Row,
    RowCreate,
    RowUpdate,
    Sheet,
    SheetCreate,
    SheetDetail,
    utc_now,
    validate_row_values,
)


class SpreadsheetStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock_path = path.with_suffix(".lock")

    def list_sheets(self, tenant_id: str, project_id: str) -> list[Sheet]:
        payload = self._load()
        project_bucket = payload.get(tenant_id, {}).get(project_id, {})
        sheets_raw = project_bucket.get("sheets", [])
        return [Sheet.model_validate(item) for item in sheets_raw]

    def create_sheet(
        self, tenant_id: str, project_id: str, payload: SheetCreate
    ) -> Sheet:
        store = self._load()
        tenant_bucket = store.setdefault(tenant_id, {})
        project_bucket = tenant_bucket.setdefault(project_id, {})
        sheets_raw = project_bucket.setdefault("sheets", [])
        if any(item.get("name") == payload.name for item in sheets_raw):
            raise ValueError("Sheet name must be unique per project")
        sheet = Sheet.build(tenant_id, project_id, payload)
        sheets_raw.append(sheet.model_dump(mode="json"))
        project_bucket.setdefault("rows", {})
        self._write(store)
        return sheet

    def get_sheet(
        self, tenant_id: str, project_id: str, sheet_id: str
    ) -> SheetDetail | None:
        store = self._load()
        project_bucket = store.get(tenant_id, {}).get(project_id, {})
        sheet_raw = self._find_sheet(project_bucket.get("sheets", []), sheet_id)
        if not sheet_raw:
            return None
        sheet = Sheet.model_validate(sheet_raw)
        rows_raw = project_bucket.get("rows", {}).get(sheet_id, [])
        rows = [Row.model_validate(item) for item in rows_raw]
        return SheetDetail(sheet=sheet, rows=rows)

    def add_row(
        self,
        tenant_id: str,
        project_id: str,
        sheet_id: str,
        payload: RowCreate,
    ) -> Row | None:
        store = self._load()
        project_bucket = store.get(tenant_id, {}).get(project_id)
        if not project_bucket:
            return None
        sheet_raw = self._find_sheet(project_bucket.get("sheets", []), sheet_id)
        if not sheet_raw:
            return None
        sheet = Sheet.model_validate(sheet_raw)
        normalized = validate_row_values(sheet.columns, payload.values, require_all=True)
        for column in sheet.columns:
            normalized.setdefault(column.column_id, None)
        row = Row.build(normalized)
        rows_bucket = project_bucket.setdefault("rows", {})
        rows_bucket.setdefault(sheet_id, []).append(row.model_dump(mode="json"))
        self._touch_sheet(sheet_raw)
        self._write(store)
        return row

    def update_row(
        self,
        tenant_id: str,
        project_id: str,
        sheet_id: str,
        row_id: str,
        payload: RowUpdate,
    ) -> Row | None:
        store = self._load()
        project_bucket = store.get(tenant_id, {}).get(project_id)
        if not project_bucket:
            return None
        sheet_raw = self._find_sheet(project_bucket.get("sheets", []), sheet_id)
        if not sheet_raw:
            return None
        sheet = Sheet.model_validate(sheet_raw)
        rows_bucket = project_bucket.get("rows", {}).get(sheet_id, [])
        for index, row_raw in enumerate(rows_bucket):
            if row_raw.get("row_id") != row_id:
                continue
            row = Row.model_validate(row_raw)
            normalized = validate_row_values(
                sheet.columns, payload.values, require_all=False
            )
            updated_values = {**row.values, **normalized}
            updated_row = row.model_copy(
                update={"values": updated_values, "updated_at": utc_now()}
            )
            rows_bucket[index] = updated_row.model_dump(mode="json")
            self._touch_sheet(sheet_raw)
            self._write(store)
            return updated_row
        return None

    def delete_row(
        self, tenant_id: str, project_id: str, sheet_id: str, row_id: str
    ) -> bool:
        store = self._load()
        project_bucket = store.get(tenant_id, {}).get(project_id)
        if not project_bucket:
            return False
        rows_bucket = project_bucket.get("rows", {}).get(sheet_id, [])
        for index, row_raw in enumerate(rows_bucket):
            if row_raw.get("row_id") == row_id:
                rows_bucket.pop(index)
                self._write(store)
                return True
        return False

    def export_csv(
        self, tenant_id: str, project_id: str, sheet_id: str
    ) -> str | None:
        detail = self.get_sheet(tenant_id, project_id, sheet_id)
        if not detail:
            return None
        output = StringIO()
        writer = csv.writer(output)
        columns = detail.sheet.columns
        writer.writerow([column.name for column in columns])
        for row in detail.rows:
            row_values = []
            for column in columns:
                value = row.values.get(column.column_id)
                if value is None:
                    row_values.append("")
                elif column.type == "bool":
                    row_values.append("true" if value else "false")
                else:
                    row_values.append(str(value))
            writer.writerow(row_values)
        return output.getvalue()

    def import_csv(
        self, tenant_id: str, project_id: str, sheet_id: str, csv_payload: str
    ) -> int | None:
        store = self._load()
        project_bucket = store.get(tenant_id, {}).get(project_id)
        if not project_bucket:
            return None
        sheet_raw = self._find_sheet(project_bucket.get("sheets", []), sheet_id)
        if not sheet_raw:
            return None
        sheet = Sheet.model_validate(sheet_raw)
        columns_by_name = {column.name: column for column in sheet.columns}
        reader = csv.DictReader(StringIO(csv_payload))
        if not reader.fieldnames:
            raise ValueError("CSV header row is required")
        unknown_headers = [
            header for header in reader.fieldnames if header not in columns_by_name
        ]
        if unknown_headers:
            raise ValueError("CSV contains unknown columns")
        missing_required = [
            column.name
            for column in sheet.columns
            if column.required and column.name not in reader.fieldnames
        ]
        if missing_required:
            raise ValueError("CSV missing required columns")

        rows_bucket = project_bucket.setdefault("rows", {})
        stored_rows = rows_bucket.setdefault(sheet_id, [])
        imported = 0
        for record in reader:
            if not any((value or "").strip() for value in record.values()):
                continue
            values: dict[str, Any] = {}
            for header, raw_value in record.items():
                column = columns_by_name.get(header)
                if not column:
                    continue
                values[column.column_id] = raw_value
            normalized = validate_row_values(sheet.columns, values, require_all=True)
            for column in sheet.columns:
                normalized.setdefault(column.column_id, None)
            row = Row.build(normalized)
            stored_rows.append(row.model_dump(mode="json"))
            imported += 1
        if imported:
            self._touch_sheet(sheet_raw)
            self._write(store)
        return imported

    def _find_sheet(self, sheets_raw: list[dict[str, Any]], sheet_id: str) -> dict[str, Any] | None:
        for sheet in sheets_raw:
            if sheet.get("sheet_id") == sheet_id:
                return sheet
        return None

    def _touch_sheet(self, sheet_raw: dict[str, Any]) -> None:
        sheet = Sheet.model_validate(sheet_raw)
        updated = sheet.model_copy(update={"updated_at": utc_now()})
        sheet_raw.clear()
        sheet_raw.update(updated.model_dump(mode="json"))

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._file_lock():
            temp_path = self._path.with_suffix(".tmp")
            with temp_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
            temp_path.replace(self._path)

    def _file_lock(self) -> "FileLock":
        return FileLock(self._lock_path)


class FileLock:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle: Any = None

    def __enter__(self) -> "FileLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self._path.open("w", encoding="utf-8")
        self._lock()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._unlock()
        if self._handle:
            self._handle.close()
            self._handle = None

    def _lock(self) -> None:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)

    def _unlock(self) -> None:
        if not self._handle:
            return
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
