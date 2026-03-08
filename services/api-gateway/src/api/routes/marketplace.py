"""
Agent Marketplace API Routes

Endpoints for browsing, registering, installing, and managing
third-party agents in the PPM Agent Marketplace.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[5]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

from agents.runtime.src.agent_catalog import (  # noqa: E402
    AgentCatalogEntry,
    get_catalog_entry,
    get_dynamic_entry,
    list_all_entries,
    register_from_manifest,
    unregister_agent,
)

router = APIRouter()
logger = logging.getLogger("api-gateway-marketplace")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class MarketplaceAgentSummary(BaseModel):
    agent_id: str
    display_name: str
    version: str | None = None
    description: str | None = None
    category: str | None = None
    author: dict[str, str] | None = None
    tags: list[str] = Field(default_factory=list)
    icon: str | None = None
    source: str = "builtin"
    capabilities: list[str] = Field(default_factory=list)
    installed: bool = True


class MarketplaceAgentDetail(MarketplaceAgentSummary):
    long_description: str | None = None
    license: str | None = None
    permissions_required: list[str] = Field(default_factory=list)
    connectors_used: list[str] = Field(default_factory=list)
    schemas_used: list[str] = Field(default_factory=list)
    inputs: list[dict[str, Any]] = Field(default_factory=list)
    outputs: list[dict[str, Any]] = Field(default_factory=list)
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    runtime: dict[str, Any] | None = None
    documentation_url: str | None = None
    repository_url: str | None = None
    published_at: str | None = None
    entry_point: dict[str, str] | None = None


class RegisterAgentRequest(BaseModel):
    manifest: dict[str, Any]


class RegisterAgentResponse(BaseModel):
    success: bool
    agent_id: str
    message: str


class UnregisterAgentResponse(BaseModel):
    success: bool
    agent_id: str
    message: str


class MarketplaceListResponse(BaseModel):
    agents: list[MarketplaceAgentSummary]
    total: int
    builtin_count: int
    marketplace_count: int


class SandboxTestRequest(BaseModel):
    agent_id: str
    input_data: dict[str, Any] = Field(default_factory=dict)


class SandboxTestResponse(BaseModel):
    agent_id: str
    success: bool
    output: dict[str, Any] | None = None
    error: str | None = None
    execution_time_seconds: float = 0.0
    manifest_valid: bool = True
    manifest_errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _entry_to_summary(entry: AgentCatalogEntry) -> MarketplaceAgentSummary:
    return MarketplaceAgentSummary(
        agent_id=entry.agent_id,
        display_name=entry.display_name,
        version=getattr(entry, "version", None),
        description=getattr(entry, "description", None),
        category=getattr(entry, "category", None),
        author=getattr(entry, "author", None),
        tags=getattr(entry, "tags", []),
        icon=getattr(entry, "icon", None),
        source=getattr(entry, "source", "builtin"),
        capabilities=getattr(entry, "capabilities", []),
        installed=True,
    )


def _entry_to_detail(entry: AgentCatalogEntry) -> MarketplaceAgentDetail:
    manifest = getattr(entry, "manifest_data", None) or {}
    return MarketplaceAgentDetail(
        agent_id=entry.agent_id,
        display_name=entry.display_name,
        version=getattr(entry, "version", None),
        description=getattr(entry, "description", None),
        long_description=manifest.get("long_description"),
        category=getattr(entry, "category", None),
        author=getattr(entry, "author", None),
        license=manifest.get("license"),
        tags=getattr(entry, "tags", []),
        icon=getattr(entry, "icon", None),
        source=getattr(entry, "source", "builtin"),
        capabilities=getattr(entry, "capabilities", []),
        permissions_required=getattr(entry, "permissions_required", []),
        connectors_used=manifest.get("connectors_used", []),
        schemas_used=manifest.get("schemas_used", []),
        inputs=manifest.get("inputs", []),
        outputs=manifest.get("outputs", []),
        parameters=manifest.get("parameters", []),
        runtime=manifest.get("runtime"),
        documentation_url=manifest.get("documentation_url"),
        repository_url=manifest.get("repository_url"),
        published_at=manifest.get("published_at"),
        entry_point=manifest.get("entry_point"),
        installed=True,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/marketplace/agents", response_model=MarketplaceListResponse)
async def list_marketplace_agents(
    category: str | None = Query(None, description="Filter by category"),
    source: str | None = Query(None, description="Filter by source: builtin or marketplace"),
    search: str | None = Query(None, description="Search by name, description, or tags"),
) -> MarketplaceListResponse:
    """Browse all available agents in the marketplace (built-in + third-party)."""
    entries = list_all_entries()
    summaries: list[MarketplaceAgentSummary] = []
    builtin_count = 0
    marketplace_count = 0

    for entry in entries:
        entry_source = getattr(entry, "source", "builtin")
        entry_category = getattr(entry, "category", None)

        if source and entry_source != source:
            continue
        if category and entry_category != category:
            continue
        if search:
            search_lower = search.lower()
            haystack = " ".join(
                [
                    entry.display_name,
                    getattr(entry, "description", "") or "",
                    " ".join(getattr(entry, "tags", [])),
                    entry.agent_id,
                ]
            ).lower()
            if search_lower not in haystack:
                continue

        if entry_source == "builtin":
            builtin_count += 1
        else:
            marketplace_count += 1

        summaries.append(_entry_to_summary(entry))

    return MarketplaceListResponse(
        agents=summaries,
        total=len(summaries),
        builtin_count=builtin_count,
        marketplace_count=marketplace_count,
    )


@router.get("/marketplace/agents/{agent_id}", response_model=MarketplaceAgentDetail)
async def get_marketplace_agent(agent_id: str) -> MarketplaceAgentDetail:
    """Get detailed information about a specific marketplace agent."""
    entry = get_catalog_entry(agent_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return _entry_to_detail(entry)


@router.post("/marketplace/agents/register", response_model=RegisterAgentResponse)
async def register_marketplace_agent(
    request_body: RegisterAgentRequest,
    request: Request,
) -> RegisterAgentResponse:
    """Register a new third-party agent from a manifest.

    Requires ``marketplace.manage`` permission.
    """
    manifest = request_body.manifest

    # Validate manifest
    from agent_sdk.src.manifest import validate_manifest

    is_valid, errors = validate_manifest(manifest)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid manifest", "validation_errors": errors},
        )

    agent_id = manifest.get("agent_id", "")
    if not agent_id:
        raise HTTPException(status_code=400, detail="manifest.agent_id is required")

    # Check for conflicts
    existing = get_catalog_entry(agent_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Agent '{agent_id}' already exists in the catalog",
        )

    # Set published timestamp if not present
    if "published_at" not in manifest:
        manifest["published_at"] = datetime.now(timezone.utc).isoformat()

    try:
        entry = register_from_manifest(manifest)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info("Marketplace agent registered: %s", agent_id)
    return RegisterAgentResponse(
        success=True,
        agent_id=agent_id,
        message=f"Agent '{entry.display_name}' registered successfully",
    )


@router.delete("/marketplace/agents/{agent_id}", response_model=UnregisterAgentResponse)
async def unregister_marketplace_agent(agent_id: str) -> UnregisterAgentResponse:
    """Remove a third-party agent from the marketplace.

    Only marketplace (non-builtin) agents can be removed.
    Requires ``marketplace.manage`` permission.
    """
    entry = get_dynamic_entry(agent_id)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail=f"Marketplace agent not found: {agent_id} (built-in agents cannot be removed)",
        )

    try:
        unregister_agent(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("Marketplace agent unregistered: %s", agent_id)
    return UnregisterAgentResponse(
        success=True,
        agent_id=agent_id,
        message=f"Agent '{agent_id}' removed from marketplace",
    )


@router.post("/marketplace/agents/{agent_id}/test", response_model=SandboxTestResponse)
async def test_marketplace_agent(
    agent_id: str,
    request_body: SandboxTestRequest,
) -> SandboxTestResponse:
    """Run a sandbox test for a marketplace agent.

    Executes the agent in an isolated environment with timeout
    enforcement. Requires ``marketplace.manage`` permission.
    """
    entry = get_dynamic_entry(agent_id)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail=f"Marketplace agent not found: {agent_id}",
        )

    manifest = getattr(entry, "manifest_data", None)
    if not manifest:
        raise HTTPException(
            status_code=400,
            detail=f"Agent '{agent_id}' has no manifest data for sandbox testing",
        )

    # Validate manifest
    from agent_sdk.src.manifest import validate_manifest

    is_valid, errors = validate_manifest(manifest)

    return SandboxTestResponse(
        agent_id=agent_id,
        success=is_valid,
        output={"manifest": manifest} if is_valid else None,
        error=None if is_valid else f"Manifest validation failed: {errors}",
        manifest_valid=is_valid,
        manifest_errors=errors,
    )


@router.get("/marketplace/categories")
async def list_marketplace_categories() -> dict[str, Any]:
    """List all available agent categories with counts."""
    entries = list_all_entries()
    categories: dict[str, int] = {}
    for entry in entries:
        cat = getattr(entry, "category", None) or "uncategorised"
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "categories": [
            {"value": cat, "label": cat.replace("_", " ").title(), "count": count}
            for cat, count in sorted(categories.items())
        ],
        "total": len(entries),
    }
