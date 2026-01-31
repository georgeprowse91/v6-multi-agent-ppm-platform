from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx


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

    def update_issue(self, issue_id: str, fields: dict[str, Any]) -> bool:
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

    def update_issue(self, issue_id: str, fields: dict[str, Any]) -> bool:
        # Mock client logs updates without making real API calls
        return True


class JiraRESTClient(JiraClient):
    def __init__(self, base_url: str, username: str, api_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth = (username, api_token)

    def fetch_issues(self, project_key: str | None = None) -> list[JiraIssue]:
        jql = "order by updated DESC"
        if project_key:
            jql = f'project = "{project_key}" order by updated DESC'
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{self.base_url}/rest/api/3/search",
                params={"jql": jql},
                auth=self.auth,
            )
            response.raise_for_status()
        data = response.json()
        issues = data.get("issues", [])
        return [self._parse_issue(issue) for issue in issues]

    def _parse_issue(self, issue: dict[str, Any]) -> JiraIssue:
        fields = issue.get("fields", {})
        status = fields.get("status", {})
        return JiraIssue(
            issue_id=str(issue.get("id", "")),
            key=issue.get("key", ""),
            summary=fields.get("summary", ""),
            status=status.get("name", ""),
            updated_at=fields.get("updated", ""),
        )

    def update_issue(self, issue_id: str, fields: dict[str, Any]) -> bool:
        with httpx.Client(timeout=10.0) as client:
            response = client.put(
                f"{self.base_url}/rest/api/3/issue/{issue_id}",
                json={"fields": fields},
                auth=self.auth,
            )
            response.raise_for_status()
        return True


def get_jira_client() -> JiraClient:
    use_mock = os.getenv("JIRA_USE_MOCK", "true").lower() != "false"
    if use_mock:
        return MockJiraClient()

    base_url = os.getenv("JIRA_BASE_URL")
    username = os.getenv("JIRA_USERNAME")
    api_token = os.getenv("JIRA_API_TOKEN")
    if base_url and username and api_token:
        return JiraRESTClient(base_url, username, api_token)
    return MockJiraClient()
