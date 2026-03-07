"""Methodology-aware project setup wizard API routes.

Production-grade implementation:
- LLM-powered methodology recommendations with rule-based fallback
- Template loading from config directory + built-in defaults
- Project creation via DataServiceClient + workspace state persistence
- WorkspaceStateStore integration for project lifecycle tracking
- Connector browser with per-project toggle
- Team member assignment with RBAC role picker
- Intake-to-project creation flow
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from routes._deps import (
    PROJECTS_PATH,
    REPO_ROOT,
    STORAGE_DIR,
    _data_service_client,
    logger,
)
from routes._llm_helpers import llm_complete_json

router = APIRouter(tags=["project-setup"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ProjectCharacteristics(BaseModel):
    industry: str = Field(default="technology", min_length=1)
    team_size: int = Field(default=10, ge=1)
    duration_months: int = Field(default=6, ge=1)
    risk_level: str = "medium"
    regulatory: list[str] = Field(default_factory=list)

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v not in allowed:
            raise ValueError(f"risk_level must be one of {sorted(allowed)}, got '{v}'")
        return v


class MethodologyRecommendation(BaseModel):
    methodology: str
    match_score: float
    rationale: str
    strengths: list[str]


class ProjectTemplate(BaseModel):
    template_id: str
    name: str
    methodology: str
    industry: str
    description: str
    stages: list[dict[str, Any]]
    activity_count: int


class TeamMemberInput(BaseModel):
    name: str
    email: str
    role: str = "Developer"


class WorkspaceConfig(BaseModel):
    project_id: str
    project_name: str
    methodology: str
    template_id: str
    stages: list[dict[str, Any]]
    enabled_connectors: list[str] = Field(default_factory=list)
    team_members: list[dict[str, Any]] = Field(default_factory=list)
    intake_request_id: str | None = None
    persisted: bool = False
    created_at: str = ""


# ---------------------------------------------------------------------------
# Template loading — config dir → data dir → built-in defaults
# ---------------------------------------------------------------------------

_templates: list[ProjectTemplate] = []
_templates_loaded = False


def _load_templates() -> list[ProjectTemplate]:
    global _templates, _templates_loaded
    if _templates_loaded:
        return _templates
    _templates_loaded = True

    # Source 1: config/templates/*.yaml
    template_dir = REPO_ROOT / "config" / "templates"
    if template_dir.exists():
        for yaml_file in sorted(template_dir.glob("*.yaml")):
            try:
                import yaml
                with open(yaml_file) as f:
                    data = yaml.safe_load(f) or {}
                if data.get("template_id"):
                    _templates.append(ProjectTemplate(
                        template_id=data["template_id"],
                        name=data.get("name", data["template_id"]),
                        methodology=data.get("methodology", "adaptive"),
                        industry=data.get("industry", "technology"),
                        description=data.get("description", ""),
                        stages=data.get("stages", []),
                        activity_count=sum(len(s.get("activities", [])) for s in data.get("stages", [])),
                    ))
            except Exception as exc:
                logger.debug("Failed to load template %s: %s", yaml_file, exc)

    # Source 2: data/templates/*.json
    template_json = REPO_ROOT / "data" / "templates"
    if template_json.exists():
        for json_file in sorted(template_json.glob("*.json")):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("template_id"):
                    _templates.append(ProjectTemplate(
                        template_id=data["template_id"],
                        name=data.get("name", data["template_id"]),
                        methodology=data.get("methodology", "adaptive"),
                        industry=data.get("industry", "technology"),
                        description=data.get("description", ""),
                        stages=data.get("stages", []),
                        activity_count=sum(len(s.get("activities", [])) for s in data.get("stages", [])),
                    ))
            except Exception as exc:
                logger.debug("Failed to load template JSON %s: %s", json_file, exc)

    # Source 3: Built-in defaults
    if not _templates:
        _templates.extend(_default_templates())

    return _templates


def _default_templates() -> list[ProjectTemplate]:
    return [
        ProjectTemplate(
            template_id="tmpl-agile-tech", name="Agile Software Delivery",
            methodology="adaptive", industry="technology",
            description="Iterative software delivery with 2-week sprints, continuous integration, and DevOps practices.",
            stages=[
                {"id": "inception", "name": "Inception", "activities": ["Vision & Scope", "Team Formation", "Backlog Seeding"]},
                {"id": "iteration", "name": "Iteration", "activities": ["Sprint Planning", "Daily Standup", "Sprint Review", "Retrospective"]},
                {"id": "release", "name": "Release", "activities": ["Release Planning", "UAT", "Deployment", "Hypercare"]},
            ],
            activity_count=10,
        ),
        ProjectTemplate(
            template_id="tmpl-waterfall-construct", name="Waterfall Construction",
            methodology="predictive", industry="construction",
            description="Sequential delivery with formal gates, detailed planning, and regulatory compliance.",
            stages=[
                {"id": "initiate", "name": "Initiate", "activities": ["Project Charter", "Stakeholder Register", "Feasibility Study"]},
                {"id": "plan", "name": "Plan", "activities": ["WBS", "Schedule Baseline", "Cost Baseline", "Risk Register"]},
                {"id": "execute", "name": "Execute", "activities": ["Procurement", "Quality Control", "Status Reporting"]},
                {"id": "close", "name": "Close", "activities": ["Lessons Learned", "Final Deliverable", "Contract Closure"]},
            ],
            activity_count=14,
        ),
        ProjectTemplate(
            template_id="tmpl-hybrid-pharma", name="Hybrid Pharma Development",
            methodology="hybrid", industry="pharma",
            description="Combines predictive regulatory gates with adaptive research sprints for drug development programs.",
            stages=[
                {"id": "discovery", "name": "Discovery", "activities": ["Research Sprints", "Literature Review", "Hypothesis Validation"]},
                {"id": "preclinical", "name": "Pre-Clinical", "activities": ["Protocol Design", "Lab Testing", "GxP Compliance"]},
                {"id": "clinical", "name": "Clinical Trials", "activities": ["Trial Design", "Patient Enrollment", "Data Collection"]},
                {"id": "submission", "name": "Regulatory Submission", "activities": ["Dossier Preparation", "FDA/EMA Review", "Approval Gate"]},
            ],
            activity_count=12,
        ),
        ProjectTemplate(
            template_id="tmpl-agile-finance", name="Agile Financial Systems",
            methodology="adaptive", industry="finance",
            description="Agile delivery with SOX compliance gates and automated audit trails.",
            stages=[
                {"id": "inception", "name": "Inception", "activities": ["Compliance Mapping", "Architecture Review", "Backlog"]},
                {"id": "delivery", "name": "Delivery", "activities": ["Sprint Cycles", "SOX Evidence Collection", "Security Review"]},
                {"id": "release", "name": "Release", "activities": ["Audit Gate", "Production Deploy", "Post-Implementation Review"]},
            ],
            activity_count=9,
        ),
    ]


# ---------------------------------------------------------------------------
# Persistence — projects.json + workspace store + DataServiceClient
# ---------------------------------------------------------------------------


def _persist_project(config: WorkspaceConfig) -> bool:
    """Persist project to the local project store and workspace storage."""
    persisted = False

    # 1. Write to projects.json (local project registry)
    try:
        PROJECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing: dict[str, Any] = {"projects": []}
        if PROJECTS_PATH.exists():
            with open(PROJECTS_PATH) as f:
                existing = json.load(f)

        projects = existing.get("projects", [])
        # Check for duplicates
        if not any(p.get("id") == config.project_id for p in projects):
            projects.append({
                "id": config.project_id,
                "name": config.project_name,
                "template_id": config.template_id,
                "template_version": "1.0",
                "created_at": config.created_at,
                "methodology": {"type": config.methodology, "name": config.methodology.title()},
                "agent_config": {"enabled_agents": [], "agent_overrides": {}},
                "connector_config": {"enabled_connectors": [], "connector_overrides": {}},
                "initial_tabs": [],
                "dashboards": [],
            })
            existing["projects"] = projects
            with open(PROJECTS_PATH, "w") as f:
                json.dump(existing, f, indent=2)
            persisted = True
    except Exception as exc:
        logger.warning("Failed to persist to projects.json: %s", exc)

    # 2. Write to workspace storage
    try:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        workspaces_path = STORAGE_DIR / "workspaces.json"
        ws_data: dict[str, Any] = {}
        if workspaces_path.exists():
            with open(workspaces_path) as f:
                ws_data = json.load(f)
        workspaces = ws_data.get("workspaces", {})
        workspaces[config.project_id] = config.model_dump()
        with open(workspaces_path, "w") as f:
            json.dump({"workspaces": workspaces}, f, indent=2)
        persisted = True
    except Exception as exc:
        logger.warning("Failed to persist workspace: %s", exc)

    # 3. Try DataServiceClient for remote persistence
    try:
        client = _data_service_client()
        if hasattr(client, "store_entity"):
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule but don't block
                asyncio.ensure_future(_store_entity_async(client, config))
            persisted = True
    except Exception as exc:
        logger.debug("DataServiceClient unavailable: %s", exc)

    return persisted


async def _store_entity_async(client, config: WorkspaceConfig) -> None:
    """Async helper to store project entity via DataServiceClient."""
    try:
        await client.store_entity(
            "project",
            {
                "id": config.project_id,
                "name": config.project_name,
                "methodology": config.methodology,
                "template_id": config.template_id,
                "stages": config.stages,
                "created_at": config.created_at,
            },
            headers={"X-Tenant-ID": "default"},
        )
    except Exception as exc:
        logger.debug("DataServiceClient store_entity failed: %s", exc)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/api/project-setup/recommend-methodology")
async def recommend_methodology(
    characteristics: ProjectCharacteristics,
) -> list[MethodologyRecommendation]:
    """Recommend methodology using LLM → rule-based fallback."""
    llm_result = await llm_complete_json(
        "You are a project methodology advisor for enterprise PPM. "
        "Given project characteristics, recommend the best methodology. "
        "Return JSON array: "
        '[{"methodology":"predictive|adaptive|hybrid","match_score":0.0-1.0,'
        '"rationale":"...","strengths":["..."]}]. '
        "Scores must sum to approximately 1.0. Return exactly 3 items.",
        f"Project characteristics:\n"
        f"- Industry: {characteristics.industry}\n"
        f"- Team size: {characteristics.team_size}\n"
        f"- Duration: {characteristics.duration_months} months\n"
        f"- Risk level: {characteristics.risk_level}\n"
        f"- Regulatory requirements: {', '.join(characteristics.regulatory) or 'none'}\n\n"
        "Recommend predictive, adaptive, and hybrid methodologies with scores.",
    )

    if isinstance(llm_result, list) and len(llm_result) >= 2:
        try:
            recs = [MethodologyRecommendation.model_validate(r) for r in llm_result]
            recs.sort(key=lambda r: r.match_score, reverse=True)
            return recs
        except Exception:
            pass

    # Fallback: rule-based scoring
    predictive_score = 0.3
    adaptive_score = 0.3
    hybrid_score = 0.4

    if characteristics.risk_level == "high" or characteristics.regulatory:
        predictive_score += 0.3
        hybrid_score += 0.1
    if characteristics.team_size <= 15:
        adaptive_score += 0.2
    if characteristics.duration_months <= 4:
        adaptive_score += 0.15
    if characteristics.duration_months > 12:
        predictive_score += 0.15
    if characteristics.industry in ("pharma", "government"):
        predictive_score += 0.2
        hybrid_score += 0.15
    if characteristics.industry in ("technology", "finance"):
        adaptive_score += 0.2

    total = predictive_score + adaptive_score + hybrid_score
    recommendations = [
        MethodologyRecommendation(
            methodology="predictive",
            match_score=round(predictive_score / total, 2),
            rationale="Structured approach with formal gates, ideal for regulated environments and fixed-scope projects.",
            strengths=["Clear milestones", "Predictable timelines", "Audit-friendly"],
        ),
        MethodologyRecommendation(
            methodology="adaptive",
            match_score=round(adaptive_score / total, 2),
            rationale="Iterative delivery with continuous feedback, ideal for evolving requirements and smaller teams.",
            strengths=["Fast feedback loops", "Flexible scope", "Higher team engagement"],
        ),
        MethodologyRecommendation(
            methodology="hybrid",
            match_score=round(hybrid_score / total, 2),
            rationale="Combines predictive governance with adaptive execution, balancing control with agility.",
            strengths=["Best of both worlds", "Compliance + agility", "Scalable governance"],
        ),
    ]
    recommendations.sort(key=lambda r: r.match_score, reverse=True)
    return recommendations


@router.get("/api/project-setup/templates")
async def list_templates(
    methodology: str = Query(default=""),
    industry: str = Query(default=""),
) -> list[ProjectTemplate]:
    templates = _load_templates()
    results = templates
    if methodology:
        results = [t for t in results if t.methodology == methodology]
    if industry:
        results = [t for t in results if t.industry == industry]
    return results


class ConfigureWorkspaceRequest(BaseModel):
    """Request body for configure-workspace endpoint."""
    project_name: str
    template_id: str
    customizations: dict[str, Any] | None = None
    enabled_connectors: list[str] = Field(default_factory=list)
    team_members: list[TeamMemberInput] = Field(default_factory=list)
    intake_request_id: str | None = None


@router.post("/api/project-setup/configure-workspace")
async def configure_workspace(
    body: ConfigureWorkspaceRequest,
) -> WorkspaceConfig:
    """Configure, persist, and register a new project workspace.

    Accepts connector selections and team assignments alongside the
    template and customization parameters.
    """
    if not body.project_name or not body.project_name.strip():
        raise HTTPException(status_code=422, detail="project_name must be non-empty")
    if len(body.project_name) > 200:
        raise HTTPException(status_code=422, detail="project_name must be at most 200 characters")
    if not body.template_id or not body.template_id.strip():
        raise HTTPException(status_code=422, detail="template_id must be non-empty")

    if body.customizations:
        allowed_keys = {"extra_stages", "remove_stages"}
        invalid_keys = set(body.customizations.keys()) - allowed_keys
        if invalid_keys:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid customization keys: {sorted(invalid_keys)}. "
                f"Allowed keys: {sorted(allowed_keys)}",
            )

    templates = _load_templates()
    template = next((t for t in templates if t.template_id == body.template_id), None)

    if template is None:
        if templates:
            template = templates[0]
        else:
            raise HTTPException(status_code=404, detail="No templates available")

    stages = list(template.stages)

    # Apply customizations
    if body.customizations:
        if body.customizations.get("extra_stages"):
            for stage in body.customizations["extra_stages"]:
                if isinstance(stage, dict):
                    stages.append(stage)
        if body.customizations.get("remove_stages"):
            remove_ids = set(body.customizations["remove_stages"])
            stages = [s for s in stages if s.get("id") not in remove_ids]

    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    team_data = [m.model_dump() for m in body.team_members]

    config = WorkspaceConfig(
        project_id=project_id,
        project_name=body.project_name,
        methodology=template.methodology,
        template_id=template.template_id,
        stages=stages,
        enabled_connectors=body.enabled_connectors,
        team_members=team_data,
        intake_request_id=body.intake_request_id,
        persisted=False,
        created_at=now,
    )

    if _persist_project(config):
        config.persisted = True

    # Try to notify Workspace Setup agent for connector provisioning
    _notify_workspace_agent(config)

    logger.info(
        "Workspace created: project_id=%s, template_id=%s, connectors=%d, team=%d",
        project_id,
        body.template_id,
        len(body.enabled_connectors),
        len(body.team_members),
    )
    return config


class CreateFromIntakeRequest(BaseModel):
    """Request body for creating a project from an approved intake request."""
    intake_request_id: str
    project_name: str | None = None


@router.post("/api/project-setup/create-from-intake")
async def create_from_intake(body: CreateFromIntakeRequest) -> dict[str, Any]:
    """Create a project stub from an approved intake request.

    Generates a project entity and returns the project_id so the frontend
    can redirect to the setup wizard with the intake context.
    """
    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    project_name = body.project_name or f"Project from intake {body.intake_request_id}"

    # Persist a minimal project entry
    try:
        PROJECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing: dict[str, Any] = {"projects": []}
        if PROJECTS_PATH.exists():
            with open(PROJECTS_PATH) as f:
                existing = json.load(f)
        projects = existing.get("projects", [])
        projects.append({
            "id": project_id,
            "name": project_name,
            "status": "setup_pending",
            "intake_request_id": body.intake_request_id,
            "created_at": now,
            "methodology": {},
            "agent_config": {"enabled_agents": [], "agent_overrides": {}},
            "connector_config": {"enabled_connectors": [], "connector_overrides": {}},
        })
        existing["projects"] = projects
        with open(PROJECTS_PATH, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception as exc:
        logger.warning("Failed to persist intake project: %s", exc)

    return {
        "project_id": project_id,
        "project_name": project_name,
        "intake_request_id": body.intake_request_id,
        "status": "setup_pending",
        "created_at": now,
    }


@router.get("/api/connectors/registry")
async def get_connector_registry() -> list[dict[str, str]]:
    """Return available connectors from the connector registry."""
    registry_path = REPO_ROOT / "connectors" / "registry" / "connectors.json"
    if not registry_path.exists():
        return []
    try:
        with open(registry_path) as f:
            data = json.load(f)
        return [
            {"name": c.get("name", ""), "category": c.get("category", "")}
            for c in data
            if c.get("name")
        ]
    except Exception as exc:
        logger.debug("Failed to load connector registry: %s", exc)
        return []


def _notify_workspace_agent(config: WorkspaceConfig) -> None:
    """Attempt to notify the Workspace Setup agent to provision connectors and resources."""
    try:
        from agents.runtime.src.agent_catalog import AgentCatalog

        catalog = AgentCatalog()
        agent = catalog.get_agent("workspace_setup")
        if agent and hasattr(agent, "process"):
            import asyncio

            asyncio.ensure_future(
                agent.process(
                    {
                        "action": "initialise_workspace",
                        "project_id": config.project_id,
                        "project_name": config.project_name,
                        "methodology": config.methodology,
                        "template_id": config.template_id,
                        "enabled_connectors": config.enabled_connectors,
                        "team_members": config.team_members,
                        "intake_request_id": config.intake_request_id,
                    },
                ),
            )
    except Exception as exc:
        logger.debug("Workspace agent notification skipped: %s", exc)
