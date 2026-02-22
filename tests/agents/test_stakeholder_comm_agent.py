import pytest
from stakeholder_communications_agent import StakeholderCommunicationsAgent


@pytest.mark.asyncio
async def test_register_stakeholder_syncs_crm_and_triggers_events(tmp_path, monkeypatch):
    agent = StakeholderCommunicationsAgent(
        config={
            "stakeholder_store_path": tmp_path / "stakeholders.json",
            "crm_base_url": "https://crm.local",
            "crm_api_key": "crm-token",
            "crm_profile_endpoint": "/stakeholders/profile",
            "crm_upsert_endpoint": "/stakeholders",
        }
    )
    await agent.initialize()

    class MockResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    def mock_get(*_args, **_kwargs):
        return MockResponse(
            200,
            {
                "id": "crm-123",
                "name": "Taylor Blake",
                "title": "VP",
                "account": "Contoso",
                "email": "taylor@example.com",
            },
        )

    def mock_post(*_args, **_kwargs):
        return MockResponse(200, {"status": "ok"})

    events = []
    workflows = []

    monkeypatch.setattr("stakeholder_communications_agent.requests.get", mock_get)
    monkeypatch.setattr("stakeholder_communications_agent.requests.post", mock_post)
    monkeypatch.setattr(
        agent, "_publish_event", lambda event_type, payload: events.append(event_type)
    )
    monkeypatch.setattr(
        agent, "_trigger_workflow", lambda event_type, payload: workflows.append(event_type)
    )

    registration = await agent.process(
        {
            "action": "register_stakeholder",
            "tenant_id": "tenant-crm",
            "stakeholder": {
                "name": "Taylor Blake",
                "email": "taylor@example.com",
                "role": "Executive Sponsor",
            },
        }
    )

    stored = agent.stakeholder_register[registration["stakeholder_id"]]
    assert stored["crm_profile"]["crm_id"] == "crm-123"
    assert "stakeholder.profile.registered" in events
    assert "stakeholder.profile.registered" in workflows


@pytest.mark.asyncio
async def test_sentiment_analysis_triggers_alert(tmp_path, monkeypatch):
    agent = StakeholderCommunicationsAgent(
        config={"stakeholder_store_path": tmp_path / "stakeholders.json"}
    )
    await agent.initialize()

    registration = await agent.process(
        {
            "action": "register_stakeholder",
            "tenant_id": "tenant-alerts",
            "stakeholder": {
                "name": "Avery Lane",
                "email": "avery@example.com",
                "role": "Sponsor",
            },
        }
    )

    async def mock_sentiment(_text):
        return {"score": -0.9, "label": "negative", "confidence": 0.9}

    alert_payloads = []

    async def mock_alert(stakeholder_id, sentiment, feedback_record):
        alert_payloads.append((stakeholder_id, sentiment, feedback_record))

    monkeypatch.setattr(agent, "_analyze_text_sentiment", mock_sentiment)
    monkeypatch.setattr(agent, "_trigger_sentiment_alert", mock_alert)

    feedback = await agent.process(
        {
            "action": "collect_feedback",
            "tenant_id": "tenant-alerts",
            "feedback": {
                "stakeholder_id": registration["stakeholder_id"],
                "project_id": "proj-1",
                "comments": "This is not going well.",
                "rating": 1,
            },
        }
    )

    assert feedback["alert_triggered"] is True
    assert alert_payloads


@pytest.mark.asyncio
async def test_generate_message_uses_openai_draft(tmp_path, monkeypatch):
    agent = StakeholderCommunicationsAgent(
        config={
            "stakeholder_store_path": tmp_path / "stakeholders.json",
            "azure_openai_endpoint": "https://openai.local",
            "azure_openai_api_key": "test-key",
            "azure_openai_deployment": "test-model",
        }
    )
    await agent.initialize()

    async def mock_openai_text(*_args, **_kwargs):
        return {"content": "Draft update", "provider": "azure_openai"}

    monkeypatch.setattr(agent, "_generate_openai_text", mock_openai_text)

    response = await agent.process(
        {
            "action": "generate_message",
            "message": {
                "subject": "Weekly Update",
                "prompt_type": "status_summary",
                "data": {"summary": "On track"},
                "stakeholder_ids": [],
            },
        }
    )

    message = agent.messages[response["message_id"]]
    assert message["content"] == "Draft update"
    assert message["review_required"] is True


@pytest.mark.asyncio
async def test_schedule_event_uses_graph_suggestions(tmp_path, monkeypatch):
    agent = StakeholderCommunicationsAgent(
        config={"stakeholder_store_path": tmp_path / "stakeholders.json"}
    )
    await agent.initialize()

    suggestion_time = "2030-01-01T10:00:00"

    async def mock_suggestions(*_args, **_kwargs):
        return [suggestion_time]

    async def mock_graph_event(event, _attachments):
        return {
            "event_id": "graph-1",
            "online_meeting_url": "https://meet",
            "scheduled_time": suggestion_time,
        }

    monkeypatch.setattr(agent, "_suggest_meeting_times", mock_suggestions)
    monkeypatch.setattr(agent, "_create_graph_event", mock_graph_event)

    response = await agent.process(
        {
            "action": "schedule_event",
            "event": {
                "title": "Stakeholder Sync",
                "duration": 30,
                "stakeholder_ids": [],
            },
        }
    )

    assert response["scheduled_time"] == suggestion_time
    assert response["meeting_suggestions"] == [suggestion_time]
