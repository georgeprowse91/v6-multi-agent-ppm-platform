"""Feedback data models for capturing user evaluations of agent outputs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Feedback:
    """User feedback associated with a specific agent execution."""

    correlation_id: str
    agent_id: str
    user_rating: int
    comments: str
    corrected_response: str | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.user_rating <= 5:
            raise ValueError("user_rating must be between 1 and 5")
        if not self.correlation_id.strip():
            raise ValueError("correlation_id is required")
        if not self.agent_id.strip():
            raise ValueError("agent_id is required")
