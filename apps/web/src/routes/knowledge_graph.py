"""Knowledge graph and AI recommendations API routes.

Uses knowledge store for real data, LLM for pattern detection
and contextual recommendation generation.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from routes._deps import _get_knowledge_store, _load_projects, logger
from routes._llm_helpers import llm_complete_json

router = APIRouter(tags=["knowledge-graph"])


_VALID_NODE_TYPES = {"lesson", "risk", "decision", "project", "entity"}
_VALID_EDGE_TYPES = {"relates_to", "caused_by", "mitigated_by", "learned_from"}


class GraphNode(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    node_type: str  # lesson, risk, decision, project, entity
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("node_type")
    @classmethod
    def node_type_must_be_valid(cls, v: str) -> str:
        if v not in _VALID_NODE_TYPES:
            raise ValueError(
                f"node_type must be one of: {', '.join(sorted(_VALID_NODE_TYPES))}"
            )
        return v


class GraphEdge(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    edge_type: str  # relates_to, caused_by, mitigated_by, learned_from

    @field_validator("edge_type")
    @classmethod
    def edge_type_must_be_valid(cls, v: str) -> str:
        if v not in _VALID_EDGE_TYPES:
            raise ValueError(
                f"edge_type must be one of: {', '.join(sorted(_VALID_EDGE_TYPES))}"
            )
        return v


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class Pattern(BaseModel):
    pattern_id: str
    title: str
    description: str
    occurrences: int
    affected_projects: list[str]
    severity: str


class Recommendation(BaseModel):
    recommendation_id: str
    title: str
    description: str
    priority: str
    source_lesson_id: str
    source_lesson_title: str
    actionable_text: str


class RecommendationRequest(BaseModel):
    project_id: str
    context_type: str = "general"
    context_id: str = ""


# Mutable graph store (populated from real data on first access)
_graph_nodes: list[GraphNode] = []
_graph_edges: list[GraphEdge] = []
_graph_initialized = False


def _ensure_graph() -> None:
    global _graph_nodes, _graph_edges, _graph_initialized
    if _graph_initialized:
        return
    _graph_initialized = True

    # Pull projects from the project store
    projects = _load_projects()
    for p in projects[:15]:
        pid = getattr(p, "id", f"proj-{len(_graph_nodes)}")
        _graph_nodes.append(GraphNode(
            id=pid,
            label=getattr(p, "name", pid),
            node_type="project",
            metadata={"status": getattr(p, "status", "active"), "health": getattr(p, "health", "green")},
        ))

    # Pull knowledge items from the knowledge store (lessons, decisions)
    try:
        ks = _get_knowledge_store()
        if hasattr(ks, "search"):
            for item in ks.search("", limit=30):
                if isinstance(item, dict):
                    nid = item.get("id", f"know-{len(_graph_nodes)}")
                    ntype = item.get("type", "lesson")
                    _graph_nodes.append(GraphNode(
                        id=nid,
                        label=item.get("title", item.get("content", "")[:60]),
                        node_type=ntype if ntype in ("lesson", "risk", "decision") else "lesson",
                        metadata=item,
                    ))
                    # Link to project if referenced
                    proj_ref = item.get("project_id") or item.get("project")
                    if proj_ref:
                        _graph_edges.append(GraphEdge(source=nid, target=proj_ref, edge_type="learned_from"))
    except Exception as exc:
        logger.debug("Knowledge store unavailable: %s", exc)

    # Infer edges between risks and projects
    for node in _graph_nodes:
        if node.node_type == "risk" and node.metadata.get("project"):
            _graph_edges.append(GraphEdge(
                source=node.id, target=node.metadata["project"], edge_type="relates_to",
            ))


@router.get("/api/knowledge/graph")
async def get_knowledge_graph(
    scope: str = Query(default="portfolio"),
    id: str = Query(default="default"),
) -> GraphData:
    _ensure_graph()
    return GraphData(nodes=_graph_nodes, edges=_graph_edges)


@router.post("/api/knowledge/graph/nodes")
async def add_graph_node(node: GraphNode) -> GraphNode:
    _ensure_graph()
    for i, existing in enumerate(_graph_nodes):
        if existing.id == node.id:
            logger.info("Updating existing graph node id=%s", node.id)
            _graph_nodes[i] = node
            return node
    logger.info("Adding graph node id=%s type=%s", node.id, node.node_type)
    _graph_nodes.append(node)
    return node


@router.post("/api/knowledge/graph/edges")
async def add_graph_edge(edge: GraphEdge) -> GraphEdge:
    _ensure_graph()
    node_ids = {n.id for n in _graph_nodes}
    missing = []
    if edge.source not in node_ids:
        missing.append(f"source '{edge.source}'")
    if edge.target not in node_ids:
        missing.append(f"target '{edge.target}'")
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Edge references non-existent node(s): {', '.join(missing)}",
        )
    logger.info(
        "Adding graph edge %s --%s--> %s", edge.source, edge.edge_type, edge.target
    )
    _graph_edges.append(edge)
    return edge


@router.get("/api/knowledge/patterns")
async def get_patterns(
    scope: str = Query(default="portfolio"),
    id: str = Query(default="default"),
) -> list[Pattern]:
    _ensure_graph()

    node_summary = [f"{n.node_type}: {n.label}" for n in _graph_nodes[:25]]
    edge_summary = [f"{e.source} --{e.edge_type}--> {e.target}" for e in _graph_edges[:25]]

    result = await llm_complete_json(
        "You are a pattern detection engine. Analyze project knowledge graph nodes and edges "
        "to find recurring patterns. Return JSON: "
        '[{"pattern_id":"pat-N","title":"...","description":"...","occurrences":N,'
        '"affected_projects":["..."],"severity":"low|medium|high"}]',
        f"Nodes:\n{chr(10).join(node_summary)}\n\nEdges:\n{chr(10).join(edge_summary)}\n\n"
        "Identify 2-4 patterns.",
    )

    if isinstance(result, list):
        return [Pattern.model_validate(p) for p in result if isinstance(p, dict)]
    if isinstance(result, dict) and "patterns" in result:
        return [Pattern.model_validate(p) for p in result["patterns"] if isinstance(p, dict)]

    # Fallback
    risk_count = sum(1 for n in _graph_nodes if n.node_type == "risk")
    patterns: list[Pattern] = []
    if risk_count >= 2:
        patterns.append(Pattern(
            pattern_id="pat-001",
            title="Multiple Active Risks",
            description=f"{risk_count} risks across portfolio projects.",
            occurrences=risk_count,
            affected_projects=[n.metadata.get("project", "") for n in _graph_nodes if n.node_type == "risk"],
            severity="medium",
        ))
    return patterns


@router.post("/api/knowledge/recommendations")
async def get_recommendations(request: RecommendationRequest) -> list[Recommendation]:
    _ensure_graph()

    lessons = [n for n in _graph_nodes if n.node_type == "lesson"]
    risks = [n for n in _graph_nodes if n.node_type == "risk"]

    lesson_texts = [f"- [{l.id}] {l.label}" for l in lessons[:10]]
    risk_texts = [f"- [{r.id}] {r.label}" for r in risks[:10]]

    result = await llm_complete_json(
        "You are a recommendation engine for project management. "
        "Return JSON array: "
        '[{"recommendation_id":"rec-N","title":"...","description":"...",'
        '"priority":"critical|important|informational",'
        '"source_lesson_id":"...","source_lesson_title":"...","actionable_text":"..."}]',
        f"Project: {request.project_id}\nContext: {request.context_type}\n\n"
        f"Lessons:\n{chr(10).join(lesson_texts) or 'None'}\n\n"
        f"Risks:\n{chr(10).join(risk_texts) or 'None'}\n\n"
        "Generate 2-4 recommendations.",
    )

    if isinstance(result, list):
        return [Recommendation.model_validate(r) for r in result if isinstance(r, dict)]
    if isinstance(result, dict) and "recommendations" in result:
        return [Recommendation.model_validate(r) for r in result["recommendations"] if isinstance(r, dict)]

    # Fallback
    recs: list[Recommendation] = []
    if risks:
        recs.append(Recommendation(
            recommendation_id="rec-001", title="Address Active Risks",
            description=f"{len(risks)} risks need mitigation.", priority="important",
            source_lesson_id=risks[0].id, source_lesson_title=risks[0].label,
            actionable_text="Assign risk owners and create mitigation plans.",
        ))
    if not lessons:
        recs.append(Recommendation(
            recommendation_id="rec-002", title="Capture Lessons Learned",
            description="No lessons captured yet.", priority="informational",
            source_lesson_id="none", source_lesson_title="No lessons",
            actionable_text="Schedule lessons-learned sessions for completed milestones.",
        ))
    return recs


@router.get("/api/knowledge/stats")
async def get_graph_stats() -> dict[str, Any]:
    _ensure_graph()
    node_types: dict[str, int] = {}
    for node in _graph_nodes:
        node_types[node.node_type] = node_types.get(node.node_type, 0) + 1
    n = len(_graph_nodes)
    return {
        "total_nodes": n,
        "total_edges": len(_graph_edges),
        "node_types": node_types,
        "density": round(len(_graph_edges) / max(n * (n - 1) / 2, 1), 3),
    }
