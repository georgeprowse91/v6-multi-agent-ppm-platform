from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class JiraIssue:
    issue_id: str
    key: str
    summary: str
    status: str
    updated_at: str


class JiraClient:
    def fetch_issues(self, project_key: str | None = None) -> list[JiraIssue]:
        raise NotImplementedError


class MockJiraClient(JiraClient):
    def fetch_issues(self, project_key: str | None = None) -> list[JiraIssue]:
        now = datetime.now(timezone.utc).isoformat()
        project = project_key or "DEMO"
        return [
            JiraIssue(
                issue_id="10001",
                key=f"{project}-101",
                summary="Align kickoff checklist",
                status="In Progress",
                updated_at=now,
            ),
            JiraIssue(
                issue_id="10002",
                key=f"{project}-102",
                summary="Prepare weekly status update",
                status="To Do",
                updated_at=now,
            ),
        ]


def get_jira_client() -> JiraClient:
    use_mock = os.getenv("JIRA_USE_MOCK", "true").lower() != "false"
    if use_mock:
        return MockJiraClient()
    return MockJiraClient()
