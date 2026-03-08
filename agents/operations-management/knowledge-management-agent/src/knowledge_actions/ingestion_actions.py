"""Source ingestion action handlers for the Knowledge Management Agent."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from knowledge_utils import extract_document_attributes, generate_ingestion_id

if TYPE_CHECKING:
    from knowledge_management_agent import KnowledgeManagementAgent


async def ingest_sources(
    agent: KnowledgeManagementAgent, tenant_id: str, sources: list[dict[str, Any]]
) -> dict[str, Any]:
    """Ingest documents from configured sources."""
    from knowledge_actions.document_actions import upload_document

    ingestion_id = await generate_ingestion_id()
    ingested_documents: list[str] = []
    source_summaries: list[dict[str, Any]] = []

    for source in sources:
        source_type = source.get("type") or source.get("source_type") or "unknown"
        if source_type == "confluence":
            documents = await _crawl_confluence(agent, source)
        elif source_type == "sharepoint":
            documents = await _crawl_sharepoint(agent, source)
        elif source_type == "github":
            documents = await _crawl_github(agent, source)
        elif source_type in {"agent_output", "cognitive_summary"}:
            documents = await _ingest_agent_outputs(source)
        else:
            documents = list(source.get("documents", []))

        processed_ids: list[str] = []
        for document in documents:
            normalized = await _normalize_ingested_document(agent, document, source_type, source)
            result = await upload_document(agent, tenant_id, normalized)
            processed_ids.append(result["document_id"])
            ingested_documents.append(result["document_id"])

        source_summaries.append(
            {
                "source_type": source_type,
                "count": len(processed_ids),
                "document_ids": processed_ids,
            }
        )

    run_record = {
        "ingestion_id": ingestion_id,
        "tenant_id": tenant_id,
        "sources": source_summaries,
        "total_documents": len(ingested_documents),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.ingestion_runs.append(run_record)

    await agent._publish_event("knowledge.ingestion.completed", run_record)

    return run_record


async def ingest_agent_output(
    agent: KnowledgeManagementAgent, tenant_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Ingest agent output summaries as knowledge artifacts."""
    from knowledge_actions.document_actions import upload_document

    document_data = await _build_agent_output_document(payload)
    result = await upload_document(agent, tenant_id, document_data)
    await agent._publish_event(
        "knowledge.agent_output.ingested",
        {"tenant_id": tenant_id, "document_id": result["document_id"]},
    )
    return result


async def handle_cognitive_summary(
    agent: KnowledgeManagementAgent, payload: dict[str, Any]
) -> None:
    """Handle summaries from other agents published to the event bus."""
    tenant_id = payload.get("tenant_id") or "default"
    try:
        await ingest_agent_output(agent, tenant_id, payload)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.warning("Failed to ingest cognitive summary: %s", exc)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _crawl_confluence(
    agent: KnowledgeManagementAgent, source: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch documents from Confluence or provided payload."""
    documents = list(source.get("documents", []))
    connector = source.get("connector")
    if connector and hasattr(connector, "read"):
        try:
            records = connector.read("pages", filters=source.get("filters"))
            documents.extend(records)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            agent.logger.warning("Confluence crawl failed: %s", exc)
        return documents

    connector = _get_confluence_connector(agent)
    if connector is None:
        return documents

    try:
        records = connector.read("pages", filters=source.get("filters"))
        documents.extend(records)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.warning("Confluence crawl failed: %s", exc)
    return documents


async def _crawl_sharepoint(
    agent: KnowledgeManagementAgent, source: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch documents from SharePoint or provided payload."""
    documents = list(source.get("documents", []))
    document_ids = source.get("document_ids", [])
    for document_id in document_ids:
        record = await agent.document_management_service.get_document(document_id)
        if record:
            documents.append(record)
    if source.get("list_documents"):
        documents.extend(
            await agent.document_management_service.list_documents(
                folder_path=source.get("folder_path"),
                filters=source.get("filters"),
                limit=source.get("limit", 100),
            )
        )
    return documents


async def _crawl_github(
    agent: KnowledgeManagementAgent, source: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch documents from GitHub or provided payload."""
    documents = list(source.get("documents", []))
    for file_record in source.get("files", []):
        documents.append(file_record)
    repo_path = source.get("repo_path")
    if repo_path:
        documents.extend(_scan_repository(agent, Path(repo_path), source))
    return documents


async def _ingest_agent_outputs(source: dict[str, Any]) -> list[dict[str, Any]]:
    documents = []
    for payload in source.get("payloads", []):
        documents.append(await _build_agent_output_document(payload))
    return documents


async def _build_agent_output_document(payload: dict[str, Any]) -> dict[str, Any]:
    source_agent = payload.get("source_agent") or payload.get("agent_id") or "agent"
    title = payload.get("title") or payload.get("summary_title") or f"Summary from {source_agent}"
    content = payload.get("summary") or payload.get("content") or payload.get("details", "")
    tags = payload.get("tags") or []
    tags.extend(["agent_summary", source_agent])
    return {
        "title": title,
        "content": content,
        "author": payload.get("author") or source_agent,
        "project_id": payload.get("project_id"),
        "program_id": payload.get("program_id"),
        "portfolio_id": payload.get("portfolio_id"),
        "tags": tags,
        "metadata": payload.get("metadata", {}),
        "source": payload.get("source") or "agent_output",
        "permissions": payload.get("permissions", {"public": False}),
        "status": payload.get("status", "draft"),
    }


async def _normalize_ingested_document(
    agent: KnowledgeManagementAgent,
    document: dict[str, Any],
    source_type: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    title = document.get("title") or document.get("name") or "Untitled"
    content = document.get("content") or document.get("body") or document.get("text") or ""
    metadata = document.get("metadata", {})
    metadata.update({"source_type": source_type, "source_id": source.get("id")})
    extracted = extract_document_attributes(content)
    metadata.update(extracted.get("metadata", {}))
    return {
        "title": title,
        "content": content,
        "author": document.get("author") or document.get("owner") or extracted.get("author"),
        "project_id": document.get("project_id") or source.get("project_id"),
        "program_id": document.get("program_id") or source.get("program_id"),
        "portfolio_id": document.get("portfolio_id") or source.get("portfolio_id"),
        "tags": document.get("tags") or source.get("tags") or extracted.get("tags") or [],
        "metadata": metadata,
        "source": source_type,
        "permissions": document.get("permissions", {"public": False}),
        "status": document.get("status", "draft"),
    }


def _get_confluence_connector(agent: KnowledgeManagementAgent) -> Any | None:
    if agent._confluence_connector is not None:
        return agent._confluence_connector
    try:
        from confluence_connector import ConfluenceConnector

        from agents.common.connector_integration import ConnectorCategory, ConnectorConfig

        connector_config = ConnectorConfig(
            connector_id="confluence",
            name="Confluence",
            category=ConnectorCategory.DOC_MGMT,
            instance_url=os.getenv("CONFLUENCE_URL", ""),
        )
        agent._confluence_connector = ConfluenceConnector(connector_config)
        return agent._confluence_connector
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.warning("Failed to initialize Confluence connector: %s", exc)
        return None


def _scan_repository(
    agent: KnowledgeManagementAgent, repo_path: Path, source: dict[str, Any]
) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    if not repo_path.exists():
        return documents
    extensions = source.get("extensions") or agent.github_extensions
    max_files = source.get("max_files", agent.ingestion_max_files)
    count = 0
    for path in repo_path.rglob("*"):
        if count >= max_files:
            break
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        try:
            content = path.read_text(errors="ignore")
        except OSError:
            continue
        documents.append(
            {
                "title": path.stem,
                "content": content,
                "author": source.get("owner"),
                "tags": source.get("tags", []),
                "metadata": {
                    "path": str(path),
                    "extension": path.suffix,
                    "repo": str(repo_path),
                    "modified_at": datetime.utcfromtimestamp(path.stat().st_mtime).isoformat(),
                },
                "source": "github",
            }
        )
        count += 1
    return documents
