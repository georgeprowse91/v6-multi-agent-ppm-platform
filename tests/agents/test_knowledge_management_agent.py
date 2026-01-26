import pytest

from knowledge_management_agent import KnowledgeManagementAgent


@pytest.mark.asyncio
async def test_knowledge_agent_persists_and_enforces_access(tmp_path):
    agent = KnowledgeManagementAgent(
        config={"document_store_path": tmp_path / "documents.json"}
    )
    await agent.initialize()

    upload = await agent.process(
        {
            "action": "upload_document",
            "tenant_id": "tenant-knowledge",
            "document": {
                "title": "Requirements Plan",
                "content": "The system shall meet availability targets.",
                "author": "alex",
                "permissions": {
                    "public": False,
                    "roles": ["pm"],
                    "attributes": {"project_id": "proj-1"},
                },
            },
        }
    )

    document_id = upload["document_id"]
    stored = agent.document_store.get("tenant-knowledge", document_id)
    assert stored is not None

    allowed = await agent.process(
        {
            "action": "get_document",
            "tenant_id": "tenant-knowledge",
            "document_id": document_id,
            "user_context": {
                "user_id": "user-1",
                "roles": ["pm"],
                "attributes": {"project_id": "proj-1"},
            },
        }
    )
    assert allowed["document_id"] == document_id

    with pytest.raises(PermissionError):
        await agent.process(
            {
                "action": "get_document",
                "tenant_id": "tenant-knowledge",
                "document_id": document_id,
                "user_context": {
                    "user_id": "user-2",
                    "roles": ["viewer"],
                    "attributes": {"project_id": "proj-2"},
                },
            }
        )
