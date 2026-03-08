"""Natural language workflow builder API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from nl_workflow import NLWorkflowParser
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/workflows/from-natural-language", tags=["nl-workflow"])
_parser = NLWorkflowParser()


class NLWorkflowRequest(BaseModel):
    description: str
    context: dict[str, Any] = Field(default_factory=dict)


class NLWorkflowRefineRequest(BaseModel):
    definition: dict[str, Any]
    feedback: str


class NLWorkflowDeployRequest(BaseModel):
    definition: dict[str, Any]
    name: str | None = None


@router.post("")
async def generate_workflow(request: NLWorkflowRequest) -> dict[str, Any]:
    definition = await _parser.parse(request.description)
    validation = _parser.validate_generated(definition)
    return {
        "definition": definition,
        "validation": validation,
        "source": "natural_language",
    }


@router.post("/refine")
async def refine_workflow(request: NLWorkflowRefineRequest) -> dict[str, Any]:
    refined = await _parser.refine(request.definition, request.feedback)
    validation = _parser.validate_generated(refined)
    return {
        "definition": refined,
        "validation": validation,
        "source": "natural_language_refined",
    }


@router.post("/deploy")
async def deploy_workflow(request: NLWorkflowDeployRequest) -> dict[str, Any]:
    validation = _parser.validate_generated(request.definition)
    if not validation.get("valid"):
        return {"deployed": False, "errors": validation.get("errors", [])}
    workflow_id = f"wf-nl-{hash(str(request.definition)) % 100000:05d}"
    return {
        "deployed": True,
        "workflow_id": workflow_id,
        "name": request.name or request.definition.get("name", "Unnamed Workflow"),
    }
