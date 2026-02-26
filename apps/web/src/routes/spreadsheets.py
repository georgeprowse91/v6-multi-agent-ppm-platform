"""Spreadsheet routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from routes._deps import _require_session, logger, spreadsheet_store
from routes._deps import (
    DeleteResult,
    ImportResult,
    Row,
    RowCreate,
    RowUpdate,
    Sheet,
    SheetCreate,
    SheetDetail,
)

router = APIRouter()


@router.get("/api/spreadsheets/{project_id}/sheets", response_model=list[Sheet])
async def list_spreadsheet_sheets(project_id: str, request: Request) -> list[Sheet]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    sheets = spreadsheet_store.list_sheets(tenant_id, project_id)
    logger.info("spreadsheet.sheet.list", extra={"tenant_id": tenant_id, "project_id": project_id})
    return sheets


@router.post("/api/spreadsheets/{project_id}/sheets", response_model=Sheet)
async def create_spreadsheet_sheet(project_id: str, payload: SheetCreate, request: Request) -> Sheet:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        sheet = spreadsheet_store.create_sheet(tenant_id, project_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info("spreadsheet.sheet.create", extra={"tenant_id": tenant_id, "project_id": project_id, "sheet_id": sheet.sheet_id})
    return sheet


@router.get("/api/spreadsheets/{project_id}/sheets/{sheet_id}", response_model=SheetDetail)
async def get_spreadsheet_sheet(project_id: str, sheet_id: str, request: Request) -> SheetDetail:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    detail = spreadsheet_store.get_sheet(tenant_id, project_id, sheet_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Sheet not found")
    logger.info("spreadsheet.sheet.get", extra={"tenant_id": tenant_id, "project_id": project_id, "sheet_id": sheet_id})
    return detail


@router.post("/api/spreadsheets/{project_id}/sheets/{sheet_id}/rows", response_model=Row)
async def add_spreadsheet_row(project_id: str, sheet_id: str, payload: RowCreate, request: Request) -> Row:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        row = spreadsheet_store.add_row(tenant_id, project_id, sheet_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Sheet not found")
    logger.info("spreadsheet.row.create", extra={"tenant_id": tenant_id, "project_id": project_id, "sheet_id": sheet_id, "row_id": row.row_id})
    return row


@router.patch("/api/spreadsheets/{project_id}/sheets/{sheet_id}/rows/{row_id}", response_model=Row)
async def update_spreadsheet_row(project_id: str, sheet_id: str, row_id: str, payload: RowUpdate, request: Request) -> Row:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        row = spreadsheet_store.update_row(tenant_id, project_id, sheet_id, row_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    logger.info("spreadsheet.row.update", extra={"tenant_id": tenant_id, "project_id": project_id, "sheet_id": sheet_id, "row_id": row_id})
    return row


@router.delete("/api/spreadsheets/{project_id}/sheets/{sheet_id}/rows/{row_id}", response_model=DeleteResult)
async def delete_spreadsheet_row(project_id: str, sheet_id: str, row_id: str, request: Request) -> DeleteResult:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    deleted = spreadsheet_store.delete_row(tenant_id, project_id, sheet_id, row_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Row not found")
    logger.info("spreadsheet.row.delete", extra={"tenant_id": tenant_id, "project_id": project_id, "sheet_id": sheet_id, "row_id": row_id})
    return DeleteResult(deleted=True, row_id=row_id)


@router.get("/api/spreadsheets/{project_id}/sheets/{sheet_id}/export.csv")
async def export_spreadsheet_csv(project_id: str, sheet_id: str, request: Request) -> Response:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    csv_payload = spreadsheet_store.export_csv(tenant_id, project_id, sheet_id)
    if csv_payload is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    logger.info("spreadsheet.csv.export", extra={"tenant_id": tenant_id, "project_id": project_id, "sheet_id": sheet_id})
    return Response(content=csv_payload, media_type="text/csv")


@router.post("/api/spreadsheets/{project_id}/sheets/{sheet_id}/import.csv", response_model=ImportResult)
async def import_spreadsheet_csv(project_id: str, sheet_id: str, request: Request) -> ImportResult:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    csv_bytes = await request.body()
    if not csv_bytes:
        raise HTTPException(status_code=422, detail="CSV payload is required")
    try:
        csv_payload = csv_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV must be UTF-8") from exc
    try:
        imported = spreadsheet_store.import_csv(tenant_id, project_id, sheet_id, csv_payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if imported is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    logger.info("spreadsheet.csv.import", extra={"tenant_id": tenant_id, "project_id": project_id, "sheet_id": sheet_id})
    return ImportResult(imported=imported)
