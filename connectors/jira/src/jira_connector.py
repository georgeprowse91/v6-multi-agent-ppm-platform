"""
Jira Connector Implementation

Implements the BaseConnector interface for Atlassian Jira integration.
Supports:
- Connection testing
- Reading issues by project key
- Reading projects

Credentials are obtained from environment variables:
- JIRA_INSTANCE_URL: The Jira instance URL (e.g., https://your-domain.atlassian.net)
- JIRA_EMAIL: Email address for authentication
- JIRA_API_TOKEN: API token for authentication
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from typing import Any

# Add SDK to path
SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import (
    BaseConnector,
    ConnectionStatus,
    ConnectionTestResult,
    ConnectorCategory,
    ConnectorConfig,
)
from http_client import HttpClient, HttpClientError, RetryConfig
from secrets import resolve_secret


class JiraConnector(BaseConnector):
    """
    Jira connector for reading and writing issues and projects.

    Environment variables required:
    - JIRA_INSTANCE_URL: The Jira instance URL
    - JIRA_EMAIL: Email address for authentication
    - JIRA_API_TOKEN: API token for authentication
    """

    CONNECTOR_ID = "jira"
    CONNECTOR_NAME = "Jira"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.PM
    SUPPORTS_WRITE = True

    def __init__(
        self,
        config: ConnectorConfig,
        client: HttpClient | None = None,
        transport: Any | None = None,
    ) -> None:
        super().__init__(config)
        self._client = client
        self._transport = transport  # For testing with mocked HTTP
        self._instance_url: str | None = None
        self._email: str | None = None
        self._api_token: str | None = None

    def write(
        self,
        resource_type: str,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Write data to Jira.

        Supported resource_type values:
        - 'issues': Create or update issues
        """
        if resource_type != "issues":
            raise ValueError(f"Unsupported resource type: {resource_type}")

        if not self._authenticated:
            if not self.authenticate():
                raise RuntimeError("Failed to authenticate with Jira")

        client = self._client or self._build_client()
        results: list[dict[str, Any]] = []

        for record in data:
            issue_id = record.get("id") or record.get("key")
            status_value = record.get("status")

            if issue_id:
                current = client.get(
                    f"/rest/api/3/issue/{issue_id}",
                    params={"fields": "summary,status,updated"},
                ).json()
                current_fields = current.get("fields", {})
                current_updated = current_fields.get("updated")
                client_updated = record.get("updated") or record.get("updated_at")
                if client_updated and current_updated and client_updated != current_updated:
                    results.append(
                        {
                            "id": current.get("id") or issue_id,
                            "key": current.get("key") or issue_id,
                            "conflict": True,
                            "message": "Conflict detected: issue has been updated in Jira.",
                            "server_updated": current_updated,
                            "client_updated": client_updated,
                        }
                    )
                    continue

                fields = self._build_issue_fields(record)
                if fields:
                    client.request(
                        "PUT",
                        f"/rest/api/3/issue/{issue_id}",
                        json={"fields": fields},
                    )
                if status_value:
                    self._transition_issue(client, issue_id, status_value)
                results.append(
                    {
                        "id": current.get("id") or issue_id,
                        "key": current.get("key") or issue_id,
                        "status": status_value or self._extract_nested(
                            current_fields, "status", "name"
                        ),
                    }
                )
                continue

            created = self._create_issue(client, record)
            created_id = created.get("id")
            created_key = created.get("key")
            if status_value and (created_id or created_key):
                self._transition_issue(client, created_key or created_id, status_value)
            results.append(
                {
                    "id": created_id,
                    "key": created_key,
                    "status": status_value,
                }
            )

        return results

    def _get_credentials(self) -> tuple[str, str, str]:
        """
        Get credentials from environment variables.

        Priority:
        1. Environment variables (JIRA_INSTANCE_URL, JIRA_EMAIL, JIRA_API_TOKEN)
        2. Config instance_url (for non-secret URL only)

        API tokens are NEVER stored in config - always from env vars.
        """
        # Get instance URL from env or config
        instance_url = resolve_secret(os.getenv("JIRA_INSTANCE_URL")) or self.config.instance_url
        if not instance_url:
            raise ValueError(
                "JIRA_INSTANCE_URL environment variable or config.instance_url is required"
            )

        # Email and API token MUST come from environment
        email = resolve_secret(os.getenv("JIRA_EMAIL"))
        if not email:
            raise ValueError("JIRA_EMAIL environment variable is required")

        api_token = resolve_secret(os.getenv("JIRA_API_TOKEN"))
        if not api_token:
            raise ValueError("JIRA_API_TOKEN environment variable is required")

        return instance_url, email, api_token

    def _build_client(self) -> HttpClient:
        """Build HTTP client with authentication."""
        if self._client:
            return self._client

        instance_url, email, api_token = self._get_credentials()
        self._instance_url = instance_url
        self._email = email
        self._api_token = api_token

        # Build Basic auth header
        token = f"{email}:{api_token}".encode("utf-8")
        auth_header = base64.b64encode(token).decode("utf-8")

        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )

        return HttpClient(
            base_url=instance_url,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
            rate_limit_per_minute=600,
            retry_config=retry_config,
            transport=self._transport,
        )

    def authenticate(self) -> bool:
        """
        Authenticate with Jira by testing API access.

        Returns True if authentication is successful.
        """
        try:
            client = self._build_client()
            # Test with a simple API call
            response = client.get("/rest/api/3/myself")
            if response.status_code == 200:
                self._authenticated = True
                self._client = client
                return True
            self._authenticated = False
            return False
        except (HttpClientError, ValueError) as e:
            self._authenticated = False
            return False

    def test_connection(self) -> ConnectionTestResult:
        """
        Test the connection to Jira.

        Tests:
        1. Credentials are valid
        2. API is accessible
        3. User has appropriate permissions
        """
        try:
            client = self._build_client()

            # Test 1: Check if we can authenticate
            response = client.get("/rest/api/3/myself")
            if response.status_code == 401:
                return ConnectionTestResult(
                    status=ConnectionStatus.UNAUTHORIZED,
                    message="Invalid credentials. Please check your email and API token.",
                )

            if response.status_code != 200:
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    message=f"API returned unexpected status: {response.status_code}",
                    details={"status_code": response.status_code},
                )

            user_data = response.json()

            # Test 2: Check project access if project_key is configured
            project_details = None
            if self.config.project_key:
                try:
                    proj_response = client.get(
                        f"/rest/api/3/project/{self.config.project_key}"
                    )
                    if proj_response.status_code == 200:
                        project_details = proj_response.json()
                    elif proj_response.status_code == 404:
                        return ConnectionTestResult(
                            status=ConnectionStatus.FAILED,
                            message=f"Project '{self.config.project_key}' not found",
                            details={"project_key": self.config.project_key},
                        )
                except HttpClientError:
                    pass  # Project check is optional

            self._authenticated = True
            self._client = client

            return ConnectionTestResult(
                status=ConnectionStatus.CONNECTED,
                message="Successfully connected to Jira",
                details={
                    "user": user_data.get("displayName", "Unknown"),
                    "email": user_data.get("emailAddress", "Unknown"),
                    "instance_url": self._instance_url,
                    "project": project_details.get("name") if project_details else None,
                },
            )

        except HttpClientError as e:
            if e.status_code == 401:
                return ConnectionTestResult(
                    status=ConnectionStatus.UNAUTHORIZED,
                    message="Invalid credentials. Please check your email and API token.",
                )
            return ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                message=f"Connection failed: {e.message}",
                details={
                    "status_code": e.status_code,
                    "response": e.response_text[:500] if e.response_text else None,
                },
            )
        except ValueError as e:
            return ConnectionTestResult(
                status=ConnectionStatus.INVALID_CONFIG,
                message=str(e),
            )
        except Exception as e:
            return ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                message=f"Unexpected error: {str(e)}",
            )

    def read(
        self,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Read data from Jira.

        Supported resource_type values:
        - 'issues': Read issues (optionally filtered by project_key in filters)
        - 'projects': Read all accessible projects

        Args:
            resource_type: 'issues' or 'projects'
            filters: Optional filters. For issues: {'project_key': 'KEY', 'jql': '...'}
            limit: Maximum records to return (default 100)
            offset: Starting offset for pagination

        Returns:
            List of records
        """
        if not self._authenticated:
            if not self.authenticate():
                raise RuntimeError("Failed to authenticate with Jira")

        client = self._client or self._build_client()
        filters = filters or {}

        if resource_type == "issues":
            return self._read_issues(client, filters, limit, offset)
        elif resource_type == "projects":
            return self._read_projects(client, limit, offset)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")

    def _read_issues(
        self,
        client: HttpClient,
        filters: dict[str, Any],
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        """Read issues from Jira."""
        # Build JQL query
        project_key = filters.get("project_key") or self.config.project_key
        jql = filters.get("jql", "")

        if project_key and not jql:
            jql = f"project = {project_key} ORDER BY updated DESC"
        elif not jql:
            jql = "ORDER BY updated DESC"

        issues: list[dict[str, Any]] = []

        response = client.get(
            "/rest/api/3/search",
            params={
                "jql": jql,
                "startAt": offset,
                "maxResults": limit,
                "fields": "summary,status,assignee,created,updated,duedate,project,issuetype,priority,description",
            },
        )

        data = response.json()
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            issues.append(
                {
                    "id": issue.get("id"),
                    "key": issue.get("key"),
                    "summary": fields.get("summary"),
                    "description": self._extract_description(fields.get("description")),
                    "status": self._extract_nested(fields, "status", "name"),
                    "status_category": self._extract_nested(
                        fields, "status", "statusCategory", "key"
                    ),
                    "assignee": self._extract_nested(fields, "assignee", "displayName"),
                    "assignee_email": self._extract_nested(
                        fields, "assignee", "emailAddress"
                    ),
                    "project_key": self._extract_nested(fields, "project", "key"),
                    "project_name": self._extract_nested(fields, "project", "name"),
                    "issue_type": self._extract_nested(fields, "issuetype", "name"),
                    "priority": self._extract_nested(fields, "priority", "name"),
                    "created": fields.get("created"),
                    "updated": fields.get("updated"),
                    "due_date": fields.get("duedate"),
                }
            )

        return issues

    def _read_projects(
        self,
        client: HttpClient,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        """Read projects from Jira."""
        projects: list[dict[str, Any]] = []

        response = client.get(
            "/rest/api/3/project/search",
            params={
                "startAt": offset,
                "maxResults": limit,
            },
        )

        data = response.json()
        for project in data.get("values", []):
            projects.append(
                {
                    "id": project.get("id"),
                    "key": project.get("key"),
                    "name": project.get("name"),
                    "description": project.get("description"),
                    "lead": self._extract_nested(project, "lead", "displayName"),
                    "lead_email": self._extract_nested(project, "lead", "emailAddress"),
                    "project_type": project.get("projectTypeKey"),
                    "style": project.get("style"),
                    "archived": project.get("archived", False),
                }
            )

        return projects

    def _extract_nested(self, data: dict[str, Any], *keys: str) -> Any | None:
        """Safely extract nested dictionary values."""
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current

    def _extract_description(self, description: Any) -> str | None:
        """Extract plain text from Atlassian Document Format (ADF)."""
        if description is None:
            return None
        if isinstance(description, str):
            return description

        # ADF format - extract text content
        if isinstance(description, dict) and description.get("type") == "doc":
            texts = []
            self._extract_text_from_adf(description, texts)
            return "\n".join(texts) if texts else None

        return str(description)

    def _extract_text_from_adf(self, node: dict[str, Any], texts: list[str]) -> None:
        """Recursively extract text from ADF nodes."""
        if node.get("type") == "text":
            text = node.get("text", "")
            if text:
                texts.append(text)
        for child in node.get("content", []):
            if isinstance(child, dict):
                self._extract_text_from_adf(child, texts)

    def _build_issue_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        fields: dict[str, Any] = {}

        summary = record.get("summary") or record.get("title")
        if summary:
            fields["summary"] = summary

        description = record.get("description")
        if description is not None:
            fields["description"] = self._format_description(description)

        due_date = record.get("due_date") or record.get("duedate")
        if due_date:
            fields["duedate"] = due_date

        issue_type = record.get("issue_type") or record.get("type")
        if issue_type:
            fields["issuetype"] = {"name": self._map_issue_type(issue_type)}

        project_key = record.get("project_key") or record.get("project")
        if project_key:
            fields["project"] = {"key": project_key}

        return fields

    def _format_description(self, description: str) -> dict[str, Any]:
        if isinstance(description, dict):
            return description
        text = str(description)
        lines = text.splitlines() or [text]
        content = []
        for line in lines:
            content.append(
                {"type": "paragraph", "content": [{"type": "text", "text": line}]}
            )
        return {"type": "doc", "version": 1, "content": content}

    def _map_issue_type(self, issue_type: str) -> str:
        normalized = issue_type.strip().lower()
        if normalized in {"story", "bug", "task"}:
            return normalized.title()
        if normalized in {"milestone", "deliverable"}:
            return "Task"
        return issue_type

    def _map_status(self, status: str) -> str:
        normalized = status.strip().lower().replace(" ", "_")
        mapping = {
            "todo": "To Do",
            "to_do": "To Do",
            "in_progress": "In Progress",
            "done": "Done",
            "blocked": "Blocked",
        }
        return mapping.get(normalized, status)

    def _transition_issue(self, client: HttpClient, issue_id: str, status: str) -> None:
        target_status = self._map_status(status)
        transitions = client.get(
            f"/rest/api/3/issue/{issue_id}/transitions"
        ).json()
        for transition in transitions.get("transitions", []):
            to_status = (transition.get("to") or {}).get("name")
            if to_status and to_status.lower() == target_status.lower():
                client.post(
                    f"/rest/api/3/issue/{issue_id}/transitions",
                    json={"transition": {"id": transition.get("id")}},
                )
                return
        raise ValueError(f"No transition found for status '{target_status}' on issue {issue_id}")

    def _create_issue(self, client: HttpClient, record: dict[str, Any]) -> dict[str, Any]:
        fields = self._build_issue_fields(record)
        if "summary" not in fields:
            raise ValueError("Issue summary is required to create a Jira issue")
        if "project" not in fields:
            project_key = self.config.project_key
            if not project_key:
                raise ValueError("Project key is required to create a Jira issue")
            fields["project"] = {"key": project_key}
        if "issuetype" not in fields:
            fields["issuetype"] = {"name": "Task"}

        response = client.post("/rest/api/3/issue", json={"fields": fields})
        return response.json()


def create_jira_connector(
    instance_url: str = "",
    project_key: str = "",
    sync_direction: str = "inbound",
    sync_frequency: str = "daily",
    transport: Any | None = None,
) -> JiraConnector:
    """
    Factory function to create a JiraConnector instance.

    Args:
        instance_url: Optional Jira instance URL (can also be set via JIRA_INSTANCE_URL env var)
        project_key: Optional default project key for filtering
        sync_direction: 'inbound', 'outbound', or 'bidirectional'
        sync_frequency: Sync frequency setting
        transport: Optional HTTP transport for testing

    Returns:
        Configured JiraConnector instance
    """
    from base_connector import SyncDirection, SyncFrequency

    config = ConnectorConfig(
        connector_id="jira",
        name="Jira",
        category=ConnectorCategory.PM,
        enabled=True,
        sync_direction=SyncDirection(sync_direction),
        sync_frequency=SyncFrequency(sync_frequency),
        instance_url=instance_url,
        project_key=project_key,
    )

    return JiraConnector(config, transport=transport)
