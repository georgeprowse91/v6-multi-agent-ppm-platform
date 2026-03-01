from __future__ import annotations

from pathlib import Path

from packages.feedback.feedback_models import Feedback
from packages.llm.src.llm.prompts import PromptRegistry
from services.feedback_service import FeedbackService


def test_low_score_feedback_auto_flags_prompt(monkeypatch, tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    feedback_db = tmp_path / "feedback.sqlite3"
    monkeypatch.setenv("PROMPT_REGISTRY_PATH", str(registry_path))

    registry = PromptRegistry(registry_path=registry_path)
    created = registry.register_prompt(
        name="summarizer",
        content="Summarize {{ text }}",
        owner="owner",
        created_by="creator",
    )

    service = FeedbackService(db_path=str(feedback_db))
    service.save_feedback(
        Feedback(
            correlation_id="corr-1",
            agent_id="test-agent-alpha",
            user_rating=1,
            comments="bad",
            prompt_name="summarizer",
            prompt_version=created.version,
        )
    )

    flagged = registry.get_prompt("summarizer", version=created.version)
    assert flagged.metadata.flagged is True
    assert flagged.metadata.flagged_reason is not None
