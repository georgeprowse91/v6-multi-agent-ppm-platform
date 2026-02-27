"""
Agent Config Service – FastAPI entry point.

Exposes REST endpoints for managing agent configuration profiles
used by runtime orchestration and governance workflows.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
_common_src = REPO_ROOT / "packages" / "common" / "src"
if str(_common_src) not in sys.path:
    sys.path.insert(0, str(_common_src))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

try:
    from observability.metrics import RequestMetricsMiddleware, configure_metrics
    from observability.tracing import TraceMiddleware, configure_tracing
    _has_observability = True
except ImportError:
    _has_observability = False

try:
    from security.api_governance import apply_api_governance, version_response_payload
    from security.auth import AuthTenantMiddleware
    _has_security = True
except ImportError:
    _has_security = False

try:
    from packages.version import API_VERSION
except ImportError:
    API_VERSION = "1.0.0"

from .agent_config_service import (  # noqa: E402
    AgentConfigStore,
    ProjectAgentConfig,
    get_agent_config_store,
)

logger = logging.getLogger("agent-config")
logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "agent-config"
    version: str = API_VERSION


class AgentConfigResponse(BaseModel):
    catalog_id: str
    agent_id: str
    display_name: str
    description: str
    category: str
    enabled: bool
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    updated_at: str
    updated_by: str | None = None


class UpdateAgentConfigRequest(BaseModel):
    enabled: bool | None = None
    parameters: list[dict[str, Any]] | None = None
    updated_by: str | None = None


class ProjectAgentConfigRequest(BaseModel):
    enabled: bool = True
    parameter_overrides: dict[str, Any] = Field(default_factory=dict)
    updated_by: str | None = None


class SyncUserRolesRequest(BaseModel):
    user_id: str
    tenant_id: str
    roles: list[str]
    display_name: str | None = None
    email: str | None = None


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agent Config Service",
        description="Centralised storage and retrieval for agent configuration profiles.",
        version=API_VERSION,
    )

    if _has_security:
        try:
            app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/version"})
        except Exception as exc:
            logger.warning("Failed to configure auth middleware: %s", exc)

    if _has_observability:
        try:
            configure_metrics("agent-config")
            configure_tracing("agent-config")
            app.add_middleware(TraceMiddleware, service_name="agent-config")
            app.add_middleware(RequestMetricsMiddleware, service_name="agent-config")
        except Exception as exc:
            logger.warning("Failed to configure observability: %s", exc)

    if _has_security:
        try:
            apply_api_governance(app, service_name="agent-config")
        except Exception as exc:
            logger.warning("Failed to apply API governance: %s", exc)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    @app.get("/healthz", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/version", tags=["health"])
    def version() -> dict[str, str]:
        if _has_security:
            return version_response_payload("agent-config")
        return {"service": "agent-config", "version": API_VERSION}

    # ------------------------------------------------------------------
    # Agent catalog endpoints
    # ------------------------------------------------------------------

    @app.get("/agents", response_model=list[AgentConfigResponse], tags=["agents"])
    def list_agents(
        category: str | None = Query(None, description="Filter by agent category"),
        enabled: bool | None = Query(None, description="Filter by enabled flag"),
    ) -> list[AgentConfigResponse]:
        """List all agent configurations, with optional filters."""
        store = get_agent_config_store()
        configs = store.list_agents()
        results: list[AgentConfigResponse] = []
        for cfg in configs:
            d = cfg.to_dict()
            if category and d.get("category") != category:
                continue
            if enabled is not None and d.get("enabled") != enabled:
                continue
            results.append(AgentConfigResponse(**d))
        return results

    @app.get("/agents/{catalog_id}", response_model=AgentConfigResponse, tags=["agents"])
    def get_agent(catalog_id: str) -> AgentConfigResponse:
        """Retrieve a single agent configuration by catalog ID."""
        store = get_agent_config_store()
        cfg = store.get_agent(catalog_id)
        if cfg is None:
            raise HTTPException(status_code=404, detail=f"Agent not found: {catalog_id}")
        return AgentConfigResponse(**cfg.to_dict())

    @app.patch("/agents/{catalog_id}", response_model=AgentConfigResponse, tags=["agents"])
    def update_agent(catalog_id: str, body: UpdateAgentConfigRequest) -> AgentConfigResponse:
        """Update enablement or parameter values for an agent."""
        store = get_agent_config_store()
        updates: dict[str, Any] = {}
        if body.enabled is not None:
            updates["enabled"] = body.enabled
        if body.parameters is not None:
            updates["parameters"] = body.parameters
        updated = store.update_agent(catalog_id, updates, updated_by=body.updated_by)
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Agent not found: {catalog_id}")
        return AgentConfigResponse(**updated.to_dict())

    # ------------------------------------------------------------------
    # Project-specific overrides
    # ------------------------------------------------------------------

    @app.get(
        "/projects/{project_id}/agents",
        response_model=list[dict[str, Any]],
        tags=["project-config"],
    )
    def list_project_agent_configs(project_id: str) -> list[dict[str, Any]]:
        """Return all agent configurations for a specific project."""
        store = get_agent_config_store()
        return [c.to_dict() for c in store.list_project_agent_configs(project_id)]

    @app.put(
        "/projects/{project_id}/agents/{agent_id}",
        response_model=dict[str, Any],
        tags=["project-config"],
    )
    def upsert_project_agent_config(
        project_id: str, agent_id: str, body: ProjectAgentConfigRequest
    ) -> dict[str, Any]:
        """Create or update a project-level agent configuration override."""
        store = get_agent_config_store()
        cfg = store.set_project_agent_config(
            project_id=project_id,
            agent_id=agent_id,
            enabled=body.enabled,
            parameter_overrides=body.parameter_overrides,
            updated_by=body.updated_by,
        )
        return cfg.to_dict()

    # ------------------------------------------------------------------
    # RBAC
    # ------------------------------------------------------------------

    @app.post("/rbac/sync", tags=["rbac"])
    def sync_user_roles(body: SyncUserRolesRequest) -> dict[str, str]:
        """Synchronise RBAC roles for a user in a tenant."""
        store = get_agent_config_store()
        store.rbac_store.sync_user_roles(
            user_id=body.user_id,
            tenant_id=body.tenant_id,
            roles=body.roles,
            display_name=body.display_name,
            email=body.email,
        )
        return {"status": "ok", "user_id": body.user_id, "tenant_id": body.tenant_id}

    @app.get("/rbac/users/{user_id}/roles", tags=["rbac"])
    def get_user_roles(user_id: str, tenant_id: str = Query(...)) -> dict[str, Any]:
        """Return the RBAC roles assigned to a user."""
        store = get_agent_config_store()
        roles = store.rbac_store.get_user_roles(user_id, tenant_id)
        can_configure = store.rbac_store.can_user_configure_agents(user_id, tenant_id)
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "roles": roles,
            "can_configure_agents": can_configure,
        }

    return app


app = create_app()
