from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[3]
SRC_DIR = TESTS_DIR.parent / "src"

sys.path.extend([str(REPO_ROOT), str(SRC_DIR)])

from knowledge_management_agent import KnowledgeManagementAgent


def build_agent(tmp_path: Path) -> KnowledgeManagementAgent:
    return KnowledgeManagementAgent(
        config={
            "document_store_path": str(tmp_path / "documents.json"),
            "knowledge_db_path": str(tmp_path / "knowledge.db"),
            "document_schema_path": "data/schemas/document.schema.json",
            "similarity_threshold": 0.0,
        }
    )


def build_agent_with_entity_backend(tmp_path: Path, backend: str) -> KnowledgeManagementAgent:
    return KnowledgeManagementAgent(
        config={
            "document_store_path": str(tmp_path / "documents.json"),
            "knowledge_db_path": str(tmp_path / "knowledge.db"),
            "document_schema_path": "data/schemas/document.schema.json",
            "similarity_threshold": 0.0,
            "entity_extraction_backend": backend,
        }
    )


@pytest.mark.anyio
async def test_ingestion_from_github_repo(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    doc_path = repo_path / "readme.md"
    doc_path.write_text("Author: Jane Doe\nDate: 2024-01-01\nTags: risk, policy\nRisk plan")

    agent = build_agent(tmp_path)
    await agent.initialize()

    result = await agent._ingest_sources(
        tenant_id="tenant-a",
        sources=[{"type": "github", "repo_path": str(repo_path), "tags": ["repo-doc"]}],
    )

    assert result["total_documents"] == 1
    assert result["sources"][0]["source_type"] == "github"


@pytest.mark.anyio
async def test_semantic_search_returns_ranked_results(tmp_path: Path) -> None:
    agent = build_agent(tmp_path)
    await agent.initialize()
    upload = await agent._upload_document(
        "tenant-a",
        {
            "title": "Security Policy",
            "content": "Access control policy for cybersecurity operations.",
            "permissions": {"public": True},
        },
    )

    result = await agent._search_documents(
        query="access control policy",
        filters={},
        access_context={"user_id": "analyst", "roles": []},
        tenant_id="tenant-a",
    )

    assert result["total_results"] >= 1
    assert result["results"][0]["document_id"] == upload["document_id"]


@pytest.mark.anyio
async def test_knowledge_graph_builds_relationships(tmp_path: Path) -> None:
    agent = build_agent(tmp_path)
    await agent.initialize()
    upload = await agent._upload_document(
        "tenant-a",
        {
            "title": "Project Atlas Update",
            "content": "Decision: proceed with rollout.\nRisk: schedule delay.",
            "permissions": {"public": True},
        },
    )

    await agent._extract_entities(upload["document_id"], "tenant-a")
    graph = await agent._build_knowledge_graph(upload["document_id"], "tenant-a")

    assert graph["relationships"] >= 0
    assert agent.graph_edges


@pytest.mark.anyio
async def test_document_curation_workflow(tmp_path: Path) -> None:
    agent = build_agent(tmp_path)
    await agent.initialize()
    upload = await agent._upload_document(
        "tenant-a",
        {
            "title": "Lessons Learned",
            "content": "Retrospective summary.",
            "permissions": {"public": True},
        },
    )

    annotation = await agent._annotate_document(
        upload["document_id"],
        {"text": "Add timeline detail"},
        {"user_id": "reviewer"},
        "tenant-a",
    )
    review = await agent._review_document(
        upload["document_id"],
        {"status": "in_review", "comments": ["Looks good"]},
        {"user_id": "reviewer"},
        "tenant-a",
    )
    approval = await agent._approve_document(
        upload["document_id"],
        {"status": "approved", "notes": "Approved"},
        {"user_id": "approver"},
        "tenant-a",
    )

    assert annotation["annotation"]["text"] == "Add timeline detail"
    assert review["review"]["status"] == "in_review"
    assert approval["approval"]["status"] == "approved"


@pytest.mark.anyio
async def test_generate_excerpts_highlights_single_query_match(tmp_path: Path) -> None:
    agent = build_agent(tmp_path)
    await agent.initialize()

    results = [
        {
            "document_id": "doc-1",
            "relevance_score": 0.91,
            "summary": "Summary",
            "document": {
                "title": "Incident policy",
                "type": "policy",
                "created_at": "2024-01-01T00:00:00Z",
                "content": "The incident response handbook defines severity levels and escalation rules.",
            },
        }
    ]

    excerpted = await agent._generate_excerpts(results, "incident")

    assert len(excerpted) == 1
    assert "<mark>incident</mark>" in excerpted[0]["excerpt"].lower()


@pytest.mark.anyio
async def test_generate_excerpts_uses_multiple_query_matches_and_window(tmp_path: Path) -> None:
    agent = build_agent(tmp_path)
    await agent.initialize()

    text = (
        "Lorem ipsum preface. "
        "Risk scoring begins after kickoff and includes supplier risk indicators. "
        "Additional guidance about schedule and budget follows in detail. "
    )
    results = [
        {
            "document_id": "doc-2",
            "relevance_score": 0.88,
            "summary": "Summary",
            "document": {
                "title": "Risk guide",
                "type": "report",
                "created_at": "2024-01-01T00:00:00Z",
                "content": text,
            },
        }
    ]

    excerpted = await agent._generate_excerpts(results, "risk supplier")
    excerpt = excerpted[0]["excerpt"].lower()

    assert "<mark>risk</mark>" in excerpt
    assert "<mark>supplier</mark>" in excerpt
    assert len(excerpted[0]["excerpt"]) <= 240


@pytest.mark.anyio
async def test_generate_excerpts_no_match_falls_back_to_leading_text(tmp_path: Path) -> None:
    agent = build_agent(tmp_path)
    await agent.initialize()

    content = "This onboarding document describes standards and checklists for reviewers."
    results = [
        {
            "document_id": "doc-3",
            "relevance_score": 0.4,
            "summary": "Summary",
            "document": {
                "title": "Onboarding",
                "type": "procedure",
                "created_at": "2024-01-01T00:00:00Z",
                "content": content,
            },
        }
    ]

    excerpted = await agent._generate_excerpts(results, "nonexistent term")

    assert excerpted[0]["excerpt"]
    assert excerpted[0]["excerpt"].startswith("This onboarding document")
    assert "<mark>" not in excerpted[0]["excerpt"]


@pytest.mark.anyio
async def test_generate_excerpts_handles_very_short_and_very_long_content(tmp_path: Path) -> None:
    agent = build_agent(tmp_path)
    await agent.initialize()

    short_results = [
        {
            "document_id": "short-doc",
            "relevance_score": 0.5,
            "summary": "Summary",
            "document": {
                "title": "Short",
                "type": "note",
                "created_at": "2024-01-01T00:00:00Z",
                "content": "短い text",
            },
        }
    ]
    long_results = [
        {
            "document_id": "long-doc",
            "relevance_score": 0.5,
            "summary": "Summary",
            "document": {
                "title": "Long",
                "type": "report",
                "created_at": "2024-01-01T00:00:00Z",
                "content": "prefix " + ("x" * 600) + " compliance marker " + ("y" * 600),
            },
        }
    ]

    short_excerpt = (await agent._generate_excerpts(short_results, "short"))[0]["excerpt"]
    long_excerpt = (await agent._generate_excerpts(long_results, "marker"))[0]["excerpt"]

    assert short_excerpt == "短い text"
    assert "<mark>marker</mark>" in long_excerpt.lower()
    assert len(long_excerpt) <= 240


@pytest.mark.anyio
async def test_entity_extraction_returns_normalized_entities_for_quality_targets(
    tmp_path: Path,
) -> None:
    agent = build_agent_with_entity_backend(tmp_path, "fallback")
    await agent.initialize()

    text = (
        "Project PRJ-2048 was approved on 2025-04-10. "
        "Alice Johnson coordinated with Acme Systems LLC for onboarding."
    )
    entities = await agent._extract_entities_from_text(text)

    by_type = {entity["type"]: entity for entity in entities}
    assert by_type["project_id"]["text"] == "PRJ-2048"
    assert by_type["date"]["text"] == "2025-04-10"
    assert by_type["person"]["text"] == "Alice Johnson"
    assert by_type["organization"]["text"] == "Acme Systems LLC"

    for entity in entities:
        assert set(entity.keys()) == {"text", "type", "score", "position", "span"}
        assert 0.0 <= entity["score"] <= 1.0
        assert entity["span"]["start"] == entity["position"]
        assert entity["span"]["end"] > entity["span"]["start"]


@pytest.mark.anyio
async def test_entity_extraction_fallback_deterministic_output(tmp_path: Path) -> None:
    agent = build_agent_with_entity_backend(tmp_path, "fallback")
    await agent.initialize()

    text = "Bob Smith updated PROJ123 on 2024-12-01 with Zenith Technologies Inc"
    first = await agent._extract_entities_from_text(text)
    second = await agent._extract_entities_from_text(text)

    assert first == second
    assert any(entity["type"] == "project_id" and entity["text"] == "PROJ123" for entity in first)
