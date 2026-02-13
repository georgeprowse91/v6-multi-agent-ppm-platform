from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.llm.src.llm.evaluation import EvaluationSample, PromptEvaluationHarness
from packages.llm.src.llm.prompts import PromptRegistry

router = APIRouter(prefix="/prompts")
registry = PromptRegistry()
evaluation_harness = PromptEvaluationHarness(registry)


class PromptCreateRequest(BaseModel):
    name: str
    content: str
    owner: str
    created_by: str
    status: str = "draft"
    experiment_tags: list[str] = Field(default_factory=list)
    defaults: dict[str, Any] = Field(default_factory=dict)
    required_variables: list[str] = Field(default_factory=list)
    environment_tags: list[str] = Field(default_factory=lambda: ["dev"])
    version_label: str | None = None


class PromptUpdateRequest(BaseModel):
    content: str | None = None
    status: str | None = None
    environment_tags: list[str] | None = None
    owner: str | None = None
    created_by: str | None = None
    version_label: str | None = None


class PromptPromotionRequest(BaseModel):
    environment: str


class PromptRenderRequest(BaseModel):
    variables: dict[str, Any]
    version: int | None = None


class EvaluationRunRequest(BaseModel):
    prompt_name: str
    prompt_version: int | None = None
    run_id: str
    samples: list[dict[str, Any]]


@router.get("")
async def list_prompts(environment: str | None = None) -> Any:
    return [p.__dict__ for p in registry.list_prompts(environment=environment)]


@router.get("/flagged")
async def list_flagged_prompts() -> Any:
    return [p.__dict__ for p in registry.list_flagged_prompts()]


@router.post("")
async def create_prompt(payload: PromptCreateRequest) -> Any:
    prompt = registry.register_prompt(**payload.model_dump())
    return prompt.__dict__


@router.put("/{name}")
async def update_prompt(name: str, payload: PromptUpdateRequest) -> Any:
    try:
        prompt = registry.update_prompt(name, **payload.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return prompt.__dict__


@router.post("/{name}/promote/{version}")
async def promote_prompt(name: str, version: int, payload: PromptPromotionRequest) -> Any:
    try:
        prompt = registry.promote_prompt(name, version, payload.environment)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return prompt.__dict__


@router.post("/{name}/render")
async def render_prompt(name: str, payload: PromptRenderRequest) -> Any:
    try:
        rendered = registry.render_prompt(name, payload.variables, version=payload.version)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"prompt": rendered}


@router.delete("/{name}")
async def delete_prompt(name: str) -> Any:
    try:
        prompt = registry.delete_prompt(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return prompt.__dict__


@router.post("/evaluations/run")
async def run_evaluation(payload: EvaluationRunRequest) -> Any:
    samples = [EvaluationSample(**item) for item in payload.samples]
    result = evaluation_harness.run_batch(
        prompt_name=payload.prompt_name,
        version=payload.prompt_version,
        samples=samples,
        run_id=payload.run_id,
    )
    return result.__dict__
