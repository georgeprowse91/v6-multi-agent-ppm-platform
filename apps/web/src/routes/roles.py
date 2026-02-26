"""Role and role-assignment management routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from routes._deps import (
    ROLES_PATH,
    RoleAssignment,
    RoleDefinition,
    _list_role_assignments,
    _list_roles,
    _load_roles_payload,
    _require_session,
    _write_json,
    permission_required,
)

router = APIRouter()


@router.get("/api/roles", response_model=list[RoleDefinition])
async def list_roles(request: Request) -> list[RoleDefinition]:
    _require_session(request)
    return _list_roles()


@router.post("/api/roles", response_model=RoleDefinition, status_code=201)
@permission_required("roles.manage")
async def create_role(payload: RoleDefinition) -> RoleDefinition:
    roles_payload = _load_roles_payload()
    roles = [RoleDefinition.model_validate(item) for item in roles_payload.get("roles", [])]
    existing_index = next((idx for idx, role in enumerate(roles) if role.id == payload.id), None)
    if existing_index is None:
        roles.append(payload)
    else:
        roles[existing_index] = payload
    _write_json(ROLES_PATH, {"roles": [role.model_dump() for role in roles], "assignments": roles_payload.get("assignments", [])})
    return payload


@router.put("/api/roles/{role_id}", response_model=RoleDefinition)
@permission_required("roles.manage")
async def update_role(role_id: str, payload: RoleDefinition) -> RoleDefinition:
    if role_id != payload.id:
        raise HTTPException(status_code=422, detail="Role ID mismatch")
    roles_payload = _load_roles_payload()
    roles = [RoleDefinition.model_validate(item) for item in roles_payload.get("roles", [])]
    existing_index = next((idx for idx, role in enumerate(roles) if role.id == role_id), None)
    if existing_index is None:
        raise HTTPException(status_code=404, detail="Role not found")
    roles[existing_index] = payload
    _write_json(ROLES_PATH, {"roles": [role.model_dump() for role in roles], "assignments": roles_payload.get("assignments", [])})
    return payload


@router.delete("/api/roles/{role_id}", status_code=204)
@permission_required("roles.manage")
async def delete_role(role_id: str) -> Response:
    roles_payload = _load_roles_payload()
    roles = [RoleDefinition.model_validate(item) for item in roles_payload.get("roles", [])]
    updated_roles = [role for role in roles if role.id != role_id]
    if len(updated_roles) == len(roles):
        raise HTTPException(status_code=404, detail="Role not found")
    assignments = [RoleAssignment.model_validate(item) for item in roles_payload.get("assignments", [])]
    for assignment in assignments:
        assignment.role_ids = [rid for rid in assignment.role_ids if rid != role_id]
    _write_json(ROLES_PATH, {"roles": [role.model_dump() for role in updated_roles], "assignments": [a.model_dump() for a in assignments]})
    return Response(status_code=204)


@router.get("/api/roles/assignments", response_model=list[RoleAssignment])
@permission_required("roles.manage")
async def list_role_assignments(request: Request) -> list[RoleAssignment]:
    _require_session(request)
    return _list_role_assignments()


@router.post("/api/roles/assignments", response_model=RoleAssignment)
@permission_required("roles.manage")
async def upsert_role_assignment(payload: RoleAssignment) -> RoleAssignment:
    roles_payload = _load_roles_payload()
    roles = roles_payload.get("roles", [])
    assignments = [RoleAssignment.model_validate(item) for item in roles_payload.get("assignments", [])]
    existing_index = next((idx for idx, a in enumerate(assignments) if a.user_id == payload.user_id), None)
    if existing_index is None:
        assignments.append(payload)
    else:
        assignments[existing_index] = payload
    _write_json(ROLES_PATH, {"roles": roles, "assignments": [a.model_dump() for a in assignments]})
    return payload
