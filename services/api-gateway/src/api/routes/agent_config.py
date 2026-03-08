"""
Agent Configuration API Routes

Provides CRUD endpoints for agent configuration management.
"""

from typing import Any, cast

from agent_config_service import (
    AgentCategory,
    get_agent_config_store,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from security.audit_log import build_event, get_audit_log_store

router = APIRouter()


# Pydantic models for API
class AgentParameterModel(BaseModel):
    """API model for agent parameter."""

    name: str
    display_name: str
    description: str
    param_type: str
    default_value: Any
    current_value: Any | None = None
    options: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    required: bool = True


class AgentConfigModel(BaseModel):
    """API model for agent configuration."""

    catalog_id: str
    agent_id: str
    display_name: str
    description: str
    category: str
    enabled: bool = True
    parameters: list[AgentParameterModel] = []
    capabilities: list[str] = []
    updated_at: str | None = None
    updated_by: str | None = None


class AgentConfigUpdateModel(BaseModel):
    """API model for updating agent configuration."""

    enabled: bool | None = None
    parameters: list[dict[str, Any]] | None = None


class ProjectAgentConfigModel(BaseModel):
    """API model for project-specific agent configuration."""

    project_id: str
    agent_id: str
    enabled: bool = True
    parameter_overrides: dict[str, Any] = {}
    updated_at: str | None = None
    updated_by: str | None = None


class ProjectAgentConfigUpdateModel(BaseModel):
    """API model for updating project agent configuration."""

    enabled: bool
    parameter_overrides: dict[str, Any] | None = None


def check_user_permission(request: Request) -> str:
    """Check if authenticated user has permission to configure agents."""
    auth = request.state.auth
    store = get_agent_config_store()
    store.sync_user_roles(
        user_id=auth.subject,
        tenant_id=auth.tenant_id,
        roles=auth.roles,
        display_name=auth.claims.get("name") if isinstance(auth.claims, dict) else None,
        email=auth.claims.get("email") if isinstance(auth.claims, dict) else None,
    )
    if store.can_user_configure_agents(auth.subject, auth.tenant_id):
        return cast(str, auth.subject)
    raise HTTPException(status_code=403, detail="User does not have permission to configure agents")


def require_agent_config_permission(request: Request) -> str:
    """Dependency that enforces agent configuration permissions."""
    return check_user_permission(request)


# Agent Configuration Endpoints
@router.get("/agents/config", response_model=list[AgentConfigModel])
async def list_agent_configs(
    response: Response,
    category: str | None = None,
    enabled: bool | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[AgentConfigModel]:
    """
    List all agent configurations.

    Optionally filter by category and/or enabled status.
    """
    store = get_agent_config_store()
    agents = store.list_agents()

    # Apply filters
    if category:
        try:
            cat = AgentCategory(category)
            agents = [a for a in agents if a.category == cat]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    if enabled is not None:
        agents = [a for a in agents if a.enabled == enabled]

    responses = [AgentConfigModel(**a.to_dict()) for a in agents]
    sliced = responses[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(responses))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@router.get("/agents/config/categories")
async def list_agent_categories() -> dict[str, list[dict[str, str]]]:
    """List all available agent categories."""
    return {
        "categories": [{"value": cat.value, "label": cat.name.title()} for cat in AgentCategory]
    }


@router.get("/agents/config/{catalog_id}", response_model=AgentConfigModel)
async def get_agent_config(catalog_id: str) -> AgentConfigModel:
    """Get configuration for a specific agent."""
    store = get_agent_config_store()
    agent = store.get_agent(catalog_id)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {catalog_id}")

    return AgentConfigModel(**agent.to_dict())


@router.patch("/agents/config/{catalog_id}", response_model=AgentConfigModel)
async def update_agent_config(
    catalog_id: str,
    updates: AgentConfigUpdateModel,
    http_request: Request,
    user_id: str = Depends(require_agent_config_permission),
) -> AgentConfigModel:
    """
    Update configuration for a specific agent.

    Requires admin or PM role.
    """
    auth = http_request.state.auth

    store = get_agent_config_store()

    update_dict: dict[str, Any] = {}
    if updates.enabled is not None:
        update_dict["enabled"] = updates.enabled
    if updates.parameters is not None:
        update_dict["parameters"] = updates.parameters

    agent = store.update_agent(catalog_id, update_dict, updated_by=user_id)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {catalog_id}")

    if updates.enabled is not None:
        action = "agent.enabled" if updates.enabled else "agent.disabled"
    else:
        action = "agent.config.updated"
    get_audit_log_store().record_event(
        build_event(
            tenant_id=auth.tenant_id,
            actor_id=auth.subject,
            actor_type="user",
            roles=auth.roles,
            action=action,
            resource_type="agent",
            resource_id=catalog_id,
            outcome="success",
            metadata={"project_scope": "global"},
        )
    )

    return AgentConfigModel(**agent.to_dict())


# Project-specific Agent Configuration Endpoints
@router.get("/projects/{project_id}/agents/config", response_model=list[ProjectAgentConfigModel])
async def list_project_agent_configs(
    project_id: str,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[ProjectAgentConfigModel]:
    """List all agent configurations for a specific project."""
    store = get_agent_config_store()
    configs = store.list_project_agent_configs(project_id)
    responses = [ProjectAgentConfigModel(**c.to_dict()) for c in configs]
    sliced = responses[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(responses))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@router.get(
    "/projects/{project_id}/agents/config/{agent_id}", response_model=ProjectAgentConfigModel | None
)
async def get_project_agent_config(
    project_id: str, agent_id: str
) -> ProjectAgentConfigModel | None:
    """Get project-specific configuration for an agent."""
    store = get_agent_config_store()
    config = store.get_project_agent_config(project_id, agent_id)

    if not config:
        return None

    return ProjectAgentConfigModel(**config.to_dict())


@router.put(
    "/projects/{project_id}/agents/config/{agent_id}", response_model=ProjectAgentConfigModel
)
async def set_project_agent_config(
    project_id: str,
    agent_id: str,
    config: ProjectAgentConfigUpdateModel,
    http_request: Request,
    user_id: str = Depends(require_agent_config_permission),
) -> ProjectAgentConfigModel:
    """
    Set project-specific configuration for an agent.

    Requires admin or PM role.
    """
    auth = http_request.state.auth

    store = get_agent_config_store()
    result = store.set_project_agent_config(
        project_id=project_id,
        agent_id=agent_id,
        enabled=config.enabled,
        parameter_overrides=config.parameter_overrides,
        updated_by=user_id,
    )

    action = "agent.enabled" if config.enabled else "agent.disabled"
    get_audit_log_store().record_event(
        build_event(
            tenant_id=auth.tenant_id,
            actor_id=auth.subject,
            actor_type="user",
            roles=auth.roles,
            action=action,
            resource_type="agent",
            resource_id=agent_id,
            outcome="success",
            metadata={"project_id": project_id},
        )
    )

    return ProjectAgentConfigModel(**result.to_dict())


@router.get("/projects/{project_id}/agents/enabled")
async def get_enabled_agents_for_project(project_id: str) -> dict[str, Any]:
    """Get list of enabled agents for a specific project."""
    store = get_agent_config_store()
    agents = store.get_enabled_agents_for_project(project_id)

    return {
        "project_id": project_id,
        "enabled_agents": [
            {
                "catalog_id": a.catalog_id,
                "agent_id": a.agent_id,
                "display_name": a.display_name,
                "category": a.category.value if hasattr(a.category, "value") else a.category,
            }
            for a in agents
        ],
        "total": len(agents),
    }


@router.get("/projects/{project_id}/agents/{agent_id}/enabled")
async def check_agent_enabled_for_project(project_id: str, agent_id: str) -> dict[str, Any]:
    """Check if a specific agent is enabled for a project."""
    store = get_agent_config_store()
    enabled = store.is_agent_enabled_for_project(project_id, agent_id)

    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "enabled": enabled,
    }
