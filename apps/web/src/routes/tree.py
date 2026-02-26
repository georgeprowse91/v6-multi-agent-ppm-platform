"""WBS tree routes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from routes._deps import _require_session, logger, tree_store
from routes._deps import (
    TreeDeleteResult,
    TreeExportResponse,
    TreeListResponse,
    TreeMoveRequest,
    TreeNode,
    TreeNodeCreate,
    TreeNodeUpdate,
)

router = APIRouter()


@router.get("/api/tree/{project_id}", response_model=TreeListResponse)
async def list_tree_nodes(project_id: str, request: Request) -> TreeListResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    nodes = tree_store.list_nodes(tenant_id, project_id)
    logger.info("tree.list", extra={"tenant_id": tenant_id, "project_id": project_id})
    return TreeListResponse(tenant_id=tenant_id, project_id=project_id, nodes=nodes)


@router.post("/api/tree/{project_id}/nodes", response_model=TreeNode)
async def create_tree_node(project_id: str, payload: TreeNodeCreate, request: Request) -> TreeNode:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        node = tree_store.create_node(tenant_id, project_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info("tree.create", extra={"tenant_id": tenant_id, "project_id": project_id, "node_id": node.node_id})
    return node


@router.patch("/api/tree/{project_id}/nodes/{node_id}", response_model=TreeNode)
async def update_tree_node(project_id: str, node_id: str, payload: TreeNodeUpdate, request: Request) -> TreeNode:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        node = tree_store.update_node(tenant_id, project_id, node_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not node:
        raise HTTPException(status_code=404, detail="Tree node not found")
    logger.info("tree.update", extra={"tenant_id": tenant_id, "project_id": project_id, "node_id": node_id})
    return node


@router.post("/api/tree/{project_id}/nodes/{node_id}/move", response_model=TreeNode)
async def move_tree_node(project_id: str, node_id: str, payload: TreeMoveRequest, request: Request) -> TreeNode:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        node = tree_store.move_node(tenant_id, project_id, node_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not node:
        raise HTTPException(status_code=404, detail="Tree node not found")
    logger.info("tree.move", extra={"tenant_id": tenant_id, "project_id": project_id, "node_id": node_id})
    return node


@router.delete("/api/tree/{project_id}/nodes/{node_id}", response_model=TreeDeleteResult)
async def delete_tree_node(project_id: str, node_id: str, request: Request) -> TreeDeleteResult:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    deleted_count = tree_store.delete_node(tenant_id, project_id, node_id)
    logger.info("tree.delete", extra={"tenant_id": tenant_id, "project_id": project_id, "node_id": node_id})
    return TreeDeleteResult(deleted=deleted_count > 0, deleted_count=deleted_count)


@router.get("/api/tree/{project_id}/export", response_model=TreeExportResponse)
async def export_tree(project_id: str, request: Request) -> TreeExportResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    nodes = tree_store.list_nodes(tenant_id, project_id)
    logger.info("tree.export", extra={"tenant_id": tenant_id, "project_id": project_id})
    return TreeExportResponse(tenant_id=tenant_id, project_id=project_id, exported_at=datetime.now(timezone.utc), nodes=nodes)
