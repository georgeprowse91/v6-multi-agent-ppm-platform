import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("requests")

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "agent-21-stakeholder-comms"
    / "src"
    / "stakeholder_communications_agent.py"
)
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
spec = importlib.util.spec_from_file_location("stakeholder_communications_agent", MODULE_PATH)
agent_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(agent_module)

StakeholderCommunicationsAgent = agent_module.StakeholderCommunicationsAgent


def test_resolve_delivery_channels_prefers_stakeholder_preferences() -> None:
    agent = StakeholderCommunicationsAgent(config={})
    message = {"channel": "preferred"}
    stakeholder = {
        "preferred_channels": ["slack", "email"],
        "communication_preferences": {"fallback_channels": ["sms"]},
    }

    channels = agent._resolve_delivery_channels(message, stakeholder)

    assert channels == ["slack", "email", "sms"]


@pytest.mark.anyio
async def test_digest_queue_and_flush(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = StakeholderCommunicationsAgent(config={"digest_window_minutes": 0})
    tenant_id = "tenant-1"
    stakeholder_id = "STK-1"
    agent.stakeholder_register[stakeholder_id] = {
        "stakeholder_id": stakeholder_id,
        "name": "Alex",
        "role": "manager",
        "preferred_channels": ["email"],
        "communication_preferences": {"preferred_channels": ["email"]},
    }
    agent.engagement_metrics[stakeholder_id] = {
        "messages_sent": 0,
        "messages_opened": 0,
        "messages_clicked": 0,
        "responses_received": 0,
        "events_attended": 0,
    }
    message = {
        "message_id": "MSG-1",
        "subject": "Digest update",
        "project_id": "PRJ-1",
        "personalized_messages": [
            {
                "stakeholder_id": stakeholder_id,
                "subject": "Risk update",
                "content": "Risk details here",
                "scheduled_time": datetime.utcnow().isoformat(),
            }
        ],
    }

    async def fake_send_via_channel(*_args, **_kwargs) -> dict[str, str]:
        return {"status": "delivered", "sent_at": datetime.utcnow().isoformat()}

    monkeypatch.setattr(agent, "_send_via_channel", fake_send_via_channel)

    queued = await agent._queue_digest_notifications(tenant_id, message)
    result = await agent._flush_digest_notifications(tenant_id, stakeholder_id)

    assert queued[0]["stakeholder_id"] == stakeholder_id
    assert result["digests"][0]["digest_items"] == 1


def test_get_template_uses_locale() -> None:
    agent = StakeholderCommunicationsAgent(config={})

    template = agent._get_template("risk_alert_summary", "fr-FR")

    assert "Résumé des risques" in template.get("subject", "")
