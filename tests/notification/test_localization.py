import pytest
from approval_workflow_agent import ApprovalWorkflowAgent


class CapturingNotificationService:
    def __init__(self):
        self.sent = []

    async def send_email(self, to, subject, body, metadata=None):
        self.sent.append({"to": to, "subject": subject, "body": body, "metadata": metadata or {}})
        return {"status": "sent"}

    async def send_teams_message(self, *args, **kwargs):
        return {"status": "sent_mock"}

    async def send_slack_message(self, *args, **kwargs):
        return {"status": "sent_mock"}

    async def send_push_notification(self, *args, **kwargs):
        return {"status": "sent_mock"}


@pytest.mark.asyncio
async def test_notification_uses_user_locale_and_falls_back_to_english(tmp_path):
    agent = ApprovalWorkflowAgent(
        config={
            "approval_store_path": str(tmp_path / "approvals.json"),
            "notification_store_path": str(tmp_path / "prefs.json"),
            "role_directory": {"project_manager": ["fr-user@example.com"]},
            "notification_routing": {
                "default": {
                    "channels": {},
                },
                "users": {
                    "fr-user@example.com": {"locale": "fr"},
                },
            },
        }
    )
    await agent.initialize()
    fake = CapturingNotificationService()
    agent.notification_service = fake

    await agent.process(
        {
            "request_type": "scope_change",
            "request_id": "REQ-LOC-1",
            "requester": "requester-1",
            "details": {"description": "Mise à jour budget", "urgency": "medium"},
            "context": {"tenant_id": "tenant-loc"},
        }
    )

    fr_email = next(message for message in fake.sent if message["to"] == "fr-user@example.com")
    assert "Approbation requise" in fr_email["subject"]

    fallback_subject = agent.template_engine.render(
        "approval_request_subject",
        "de",
        {"description": "Fallback"},
    )
    assert "Approval required" in fallback_subject
    await agent.cleanup()


@pytest.mark.asyncio
async def test_notification_accessible_format_renders_html_and_persists_preferences(tmp_path):
    agent = ApprovalWorkflowAgent(
        config={
            "approval_store_path": str(tmp_path / "approvals.json"),
            "notification_store_path": str(tmp_path / "prefs.json"),
            "role_directory": {"project_manager": ["accessible@example.com"]},
            "notification_routing": {
                "default": {
                    "channels": {"email": {"address": "accessible@example.com"}},
                    "locale": "en",
                    "accessible_format": "html_with_alt_text",
                }
            },
        }
    )
    await agent.initialize()
    fake = CapturingNotificationService()
    agent.notification_service = fake

    await agent.process(
        {
            "request_type": "resource_change",
            "request_id": "REQ-ACC-1",
            "requester": "requester-1",
            "details": {"description": "Accessibility check", "urgency": "high"},
            "context": {"tenant_id": "tenant-acc"},
        }
    )

    sent = fake.sent[0]
    html_body = sent["metadata"].get("html_body")
    assert html_body
    assert "font-size:18px" in html_body
    assert sent["metadata"]["accessible_format"] == "html_with_alt_text"

    await agent.process(
        {
            "action": "subscribe_notifications",
            "tenant_id": "tenant-acc",
            "recipient": "pref-user",
            "preferences": {"channels": {"email": {"address": "pref-user@example.com"}}},
        }
    )
    stored = agent.notification_store.get_preferences("tenant-acc", "pref-user")
    assert stored["locale"] == "en"
    assert stored["accessible_format"] == "text_only"
    await agent.cleanup()
