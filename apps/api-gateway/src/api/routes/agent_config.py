"""
Agent Configuration API Routes

Provides CRUD endpoints for agent configuration management.
"""

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

# Add services to path
REPO_ROOT = Path(__file__).resolve().parents[5]
SERVICES_ROOT = REPO_ROOT / "services" / "agent-config" / "src"
if str(SERVICES_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICES_ROOT))

from agent_config_service import (
    AgentCategory,
    get_agent_config_store,
)

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


class DevUserModel(BaseModel):
    """API model for development user profile."""
    user_id: str
    name: str
    email: str
    role: str
    tenant_id: str = "default"


# Helper to get current user (stub for RBAC)
def get_current_user_id(x_user_id: str | None = Header(None, alias="X-User-Id")) -> str:
    """Get current user ID from header or default to 'admin'."""
    return x_user_id or "admin"


def check_user_permission(user_id: str) -> None:
    """Check if user has permission to configure agents."""
    store = get_agent_config_store()
    if not store.can_user_configure_agents(user_id):
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to configure agents"
        )


# Agent Configuration Endpoints
@router.get("/agents/config", response_model=list[AgentConfigModel])
async def list_agent_configs(
    category: str | None = None,
    enabled: bool | None = None,
):
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

    return [AgentConfigModel(**a.to_dict()) for a in agents]


@router.get("/agents/config/categories")
async def list_agent_categories():
    """List all available agent categories."""
    return {
        "categories": [
            {"value": cat.value, "label": cat.name.title()}
            for cat in AgentCategory
        ]
    }


@router.get("/agents/config/{catalog_id}", response_model=AgentConfigModel)
async def get_agent_config(catalog_id: str):
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
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Update configuration for a specific agent.

    Requires admin or PM role.
    """
    user_id = get_current_user_id(x_user_id)
    check_user_permission(user_id)

    store = get_agent_config_store()

    update_dict = {}
    if updates.enabled is not None:
        update_dict["enabled"] = updates.enabled
    if updates.parameters is not None:
        update_dict["parameters"] = updates.parameters

    agent = store.update_agent(catalog_id, update_dict, updated_by=user_id)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {catalog_id}")

    return AgentConfigModel(**agent.to_dict())


# Project-specific Agent Configuration Endpoints
@router.get("/projects/{project_id}/agents/config", response_model=list[ProjectAgentConfigModel])
async def list_project_agent_configs(project_id: str):
    """List all agent configurations for a specific project."""
    store = get_agent_config_store()
    configs = store.list_project_agent_configs(project_id)
    return [ProjectAgentConfigModel(**c.to_dict()) for c in configs]


@router.get("/projects/{project_id}/agents/config/{agent_id}", response_model=ProjectAgentConfigModel | None)
async def get_project_agent_config(project_id: str, agent_id: str):
    """Get project-specific configuration for an agent."""
    store = get_agent_config_store()
    config = store.get_project_agent_config(project_id, agent_id)

    if not config:
        return None

    return ProjectAgentConfigModel(**config.to_dict())


@router.put("/projects/{project_id}/agents/config/{agent_id}", response_model=ProjectAgentConfigModel)
async def set_project_agent_config(
    project_id: str,
    agent_id: str,
    config: ProjectAgentConfigUpdateModel,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Set project-specific configuration for an agent.

    Requires admin or PM role.
    """
    user_id = get_current_user_id(x_user_id)
    check_user_permission(user_id)

    store = get_agent_config_store()
    result = store.set_project_agent_config(
        project_id=project_id,
        agent_id=agent_id,
        enabled=config.enabled,
        parameter_overrides=config.parameter_overrides,
        updated_by=user_id,
    )

    return ProjectAgentConfigModel(**result.to_dict())


@router.get("/projects/{project_id}/agents/enabled")
async def get_enabled_agents_for_project(project_id: str):
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
                "category": a.category.value if hasattr(a.category, 'value') else a.category,
            }
            for a in agents
        ],
        "total": len(agents),
    }


@router.get("/projects/{project_id}/agents/{agent_id}/enabled")
async def check_agent_enabled_for_project(project_id: str, agent_id: str):
    """Check if a specific agent is enabled for a project."""
    store = get_agent_config_store()
    enabled = store.is_agent_enabled_for_project(project_id, agent_id)

    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "enabled": enabled,
    }


# Dev User Endpoints (RBAC stub)
@router.get("/users/dev", response_model=list[DevUserModel])
async def list_dev_users():
    """List all development user profiles (for testing RBAC)."""
    store = get_agent_config_store()
    users = store.list_dev_users()
    return [DevUserModel(**u.to_dict()) for u in users]


@router.get("/users/dev/{user_id}", response_model=DevUserModel | None)
async def get_dev_user(user_id: str):
    """Get a specific development user profile."""
    store = get_agent_config_store()
    user = store.get_dev_user(user_id)

    if not user:
        return None

    return DevUserModel(**user.to_dict())


@router.get("/users/dev/{user_id}/can-configure")
async def check_user_can_configure(user_id: str):
    """Check if a user can configure agents."""
    store = get_agent_config_store()
    can_configure = store.can_user_configure_agents(user_id)

    return {
        "user_id": user_id,
        "can_configure_agents": can_configure,
    }
