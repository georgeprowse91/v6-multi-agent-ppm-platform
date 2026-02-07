"""
Tests for the Jira Connector

Uses mocked HTTP client to test connection testing and issue reading
without requiring actual Jira credentials.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest

# Add connector paths
REPO_ROOT = Path(__file__).resolve().parents[4]
CONNECTOR_SDK_PATH = REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"
JIRA_CONNECTOR_PATH = REPO_ROOT / "integrations" / "connectors" / "jira" / "src"
for path in (CONNECTOR_SDK_PATH, JIRA_CONNECTOR_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from base_connector import (
    ConnectionStatus,
    ConnectorCategory,
    ConnectorConfig,
    SyncDirection,
    SyncFrequency,
)
from jira_connector import JiraConnector, create_jira_connector


class MockTransport(httpx.BaseTransport):
    """Mock HTTP transport for testing."""

    def __init__(self, responses: dict[str, Any] | None = None):
        self._responses = responses or {}
        self._requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self._requests.append(request)
        url_path = request.url.path

        # Check if we have a mock response for this path
        for path_pattern, response_data in self._responses.items():
            if path_pattern in url_path:
                status_code = response_data.get("status_code", 200)
                content = response_data.get("content", {})
                return httpx.Response(
                    status_code=status_code,
                    json=content,
                    request=request,
                )

        # Default 404 response
        return httpx.Response(
            status_code=404,
            json={"error": "Not found"},
            request=request,
        )

    @property
    def requests(self) -> list[httpx.Request]:
        return self._requests


@pytest.fixture
def mock_env():
    """Set up mock environment variables for Jira credentials."""
    env_vars = {
        "JIRA_INSTANCE_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-api-token",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def jira_config():
    """Create a basic Jira connector config."""
    return ConnectorConfig(
        connector_id="jira",
        name="Jira",
        category=ConnectorCategory.PM,
        enabled=True,
        sync_direction=SyncDirection.INBOUND,
        sync_frequency=SyncFrequency.DAILY,
        instance_url="https://test.atlassian.net",
        project_key="TEST",
    )


@pytest.fixture
def mock_myself_response():
    """Mock response for /rest/api/3/myself endpoint."""
    return {
        "accountId": "123456789",
        "displayName": "Test User",
        "emailAddress": "test@example.com",
        "active": True,
    }


@pytest.fixture
def mock_project_response():
    """Mock response for /rest/api/3/project/{key} endpoint."""
    return {
        "id": "10000",
        "key": "TEST",
        "name": "Test Project",
        "description": "A test project",
        "lead": {
            "displayName": "Project Lead",
            "emailAddress": "lead@example.com",
        },
        "projectTypeKey": "software",
    }


@pytest.fixture
def mock_issues_response():
    """Mock response for /rest/api/3/search endpoint."""
    return {
        "startAt": 0,
        "maxResults": 50,
        "total": 2,
        "issues": [
            {
                "id": "10001",
                "key": "TEST-1",
                "fields": {
                    "summary": "Test Issue 1",
                    "description": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": "Issue description"}
                                ],
                            }
                        ],
                    },
                    "status": {
                        "name": "To Do",
                        "statusCategory": {"key": "new"},
                    },
                    "assignee": {
                        "displayName": "Assignee User",
                        "emailAddress": "assignee@example.com",
                    },
                    "project": {
                        "key": "TEST",
                        "name": "Test Project",
                    },
                    "issuetype": {"name": "Task"},
                    "priority": {"name": "Medium"},
                    "created": "2024-01-15T10:00:00.000+0000",
                    "updated": "2024-01-16T14:30:00.000+0000",
                    "duedate": "2024-02-01",
                },
            },
            {
                "id": "10002",
                "key": "TEST-2",
                "fields": {
                    "summary": "Test Issue 2",
                    "description": None,
                    "status": {
                        "name": "Done",
                        "statusCategory": {"key": "done"},
                    },
                    "assignee": None,
                    "project": {
                        "key": "TEST",
                        "name": "Test Project",
                    },
                    "issuetype": {"name": "Bug"},
                    "priority": {"name": "High"},
                    "created": "2024-01-10T09:00:00.000+0000",
                    "updated": "2024-01-18T11:00:00.000+0000",
                    "duedate": None,
                },
            },
        ],
    }


@pytest.fixture
def mock_projects_response():
    """Mock response for /rest/api/3/project/search endpoint."""
    return {
        "startAt": 0,
        "maxResults": 50,
        "total": 1,
        "isLast": True,
        "values": [
            {
                "id": "10000",
                "key": "TEST",
                "name": "Test Project",
                "description": "A test project",
                "lead": {
                    "displayName": "Project Lead",
                    "emailAddress": "lead@example.com",
                },
                "projectTypeKey": "software",
                "style": "classic",
                "archived": False,
            }
        ],
    }


class TestJiraConnectorAuthentication:
    """Tests for Jira connector authentication."""

    def test_authenticate_success(
        self, mock_env, jira_config, mock_myself_response
    ):
        """Test successful authentication."""
        transport = MockTransport(
            {"/rest/api/3/myself": {"status_code": 200, "content": mock_myself_response}}
        )
        connector = JiraConnector(jira_config, transport=transport)

        result = connector.authenticate()

        assert result is True
        assert connector.is_authenticated is True
        assert len(transport.requests) == 1
        assert "/rest/api/3/myself" in str(transport.requests[0].url)

    def test_authenticate_failure_unauthorized(self, mock_env, jira_config):
        """Test authentication failure with 401 response."""
        transport = MockTransport(
            {"/rest/api/3/myself": {"status_code": 401, "content": {"error": "Unauthorized"}}}
        )
        connector = JiraConnector(jira_config, transport=transport)

        result = connector.authenticate()

        assert result is False
        assert connector.is_authenticated is False

    def test_authenticate_missing_credentials(self, jira_config):
        """Test authentication with missing credentials."""
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            connector = JiraConnector(jira_config)
            result = connector.authenticate()

            assert result is False
            assert connector.is_authenticated is False


class TestJiraConnectorTestConnection:
    """Tests for Jira connector connection testing."""

    def test_test_connection_success(
        self, mock_env, jira_config, mock_myself_response, mock_project_response
    ):
        """Test successful connection test."""
        transport = MockTransport(
            {
                "/rest/api/3/myself": {"status_code": 200, "content": mock_myself_response},
                "/rest/api/3/project/TEST": {"status_code": 200, "content": mock_project_response},
            }
        )
        connector = JiraConnector(jira_config, transport=transport)

        result = connector.test_connection()

        assert result.status == ConnectionStatus.CONNECTED
        assert "Successfully connected" in result.message
        assert result.details["user"] == "Test User"
        assert result.details["email"] == "test@example.com"
        assert result.details["project"] == "Test Project"

    def test_test_connection_unauthorized(self, mock_env, jira_config):
        """Test connection test with invalid credentials."""
        transport = MockTransport(
            {"/rest/api/3/myself": {"status_code": 401, "content": {"error": "Unauthorized"}}}
        )
        connector = JiraConnector(jira_config, transport=transport)

        result = connector.test_connection()

        assert result.status == ConnectionStatus.UNAUTHORIZED
        assert "Invalid credentials" in result.message

    def test_test_connection_project_not_found_still_connects(
        self, mock_env, jira_config, mock_myself_response
    ):
        """Test connection test succeeds even when project is not found (project check is optional)."""
        transport = MockTransport(
            {
                "/rest/api/3/myself": {"status_code": 200, "content": mock_myself_response},
                "/rest/api/3/project/TEST": {"status_code": 404, "content": {"error": "Not found"}},
            }
        )
        connector = JiraConnector(jira_config, transport=transport)

        result = connector.test_connection()

        # Connection succeeds because project check is optional - authentication worked
        assert result.status == ConnectionStatus.CONNECTED
        assert result.details.get("project") is None  # No project details since 404

    def test_test_connection_missing_credentials(self, jira_config):
        """Test connection test with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            connector = JiraConnector(jira_config)
            result = connector.test_connection()

            assert result.status == ConnectionStatus.INVALID_CONFIG
            assert "required" in result.message.lower()


class TestJiraConnectorReadIssues:
    """Tests for Jira connector issue reading."""

    def test_read_issues_success(
        self, mock_env, jira_config, mock_myself_response, mock_issues_response
    ):
        """Test successful issue reading."""
        transport = MockTransport(
            {
                "/rest/api/3/myself": {"status_code": 200, "content": mock_myself_response},
                "/rest/api/3/search": {"status_code": 200, "content": mock_issues_response},
            }
        )
        connector = JiraConnector(jira_config, transport=transport)
        connector.authenticate()

        issues = connector.read("issues", filters={"project_key": "TEST"})

        assert len(issues) == 2

        # Check first issue
        issue1 = issues[0]
        assert issue1["key"] == "TEST-1"
        assert issue1["summary"] == "Test Issue 1"
        assert issue1["status"] == "To Do"
        assert issue1["assignee"] == "Assignee User"
        assert issue1["project_key"] == "TEST"
        assert issue1["issue_type"] == "Task"
        assert issue1["priority"] == "Medium"
        assert "Issue description" in (issue1["description"] or "")

        # Check second issue
        issue2 = issues[1]
        assert issue2["key"] == "TEST-2"
        assert issue2["summary"] == "Test Issue 2"
        assert issue2["status"] == "Done"
        assert issue2["assignee"] is None
        assert issue2["description"] is None

    def test_read_issues_with_jql(
        self, mock_env, jira_config, mock_myself_response, mock_issues_response
    ):
        """Test reading issues with custom JQL filter."""
        transport = MockTransport(
            {
                "/rest/api/3/myself": {"status_code": 200, "content": mock_myself_response},
                "/rest/api/3/search": {"status_code": 200, "content": mock_issues_response},
            }
        )
        connector = JiraConnector(jira_config, transport=transport)
        connector.authenticate()

        issues = connector.read(
            "issues",
            filters={"jql": "status = 'To Do' ORDER BY created DESC"},
        )

        assert len(issues) == 2
        # Verify the request was made with the JQL
        search_request = [r for r in transport.requests if "/search" in str(r.url)][0]
        assert "jql" in str(search_request.url)


class TestJiraConnectorReadProjects:
    """Tests for Jira connector project reading."""

    def test_read_projects_success(
        self, mock_env, jira_config, mock_myself_response, mock_projects_response
    ):
        """Test successful project reading."""
        transport = MockTransport(
            {
                "/rest/api/3/myself": {"status_code": 200, "content": mock_myself_response},
                "/rest/api/3/project/search": {"status_code": 200, "content": mock_projects_response},
            }
        )
        connector = JiraConnector(jira_config, transport=transport)
        connector.authenticate()

        projects = connector.read("projects")

        assert len(projects) == 1
        project = projects[0]
        assert project["key"] == "TEST"
        assert project["name"] == "Test Project"
        assert project["lead"] == "Project Lead"
        assert project["project_type"] == "software"
        assert project["archived"] is False


class TestJiraConnectorFactory:
    """Tests for the Jira connector factory function."""

    def test_create_jira_connector_defaults(self, mock_env):
        """Test creating connector with default settings."""
        connector = create_jira_connector()

        assert connector.CONNECTOR_ID == "jira"
        assert connector.config.sync_direction == SyncDirection.INBOUND
        assert connector.config.sync_frequency == SyncFrequency.DAILY

    def test_create_jira_connector_custom_settings(self, mock_env):
        """Test creating connector with custom settings."""
        connector = create_jira_connector(
            instance_url="https://custom.atlassian.net",
            project_key="CUSTOM",
            sync_frequency="hourly",
        )

        assert connector.config.instance_url == "https://custom.atlassian.net"
        assert connector.config.project_key == "CUSTOM"
        assert connector.config.sync_frequency == SyncFrequency.HOURLY


class TestJiraConnectorUnsupportedOperations:
    """Tests for unsupported connector operations."""

    def test_read_unsupported_resource_type(self, mock_env, jira_config, mock_myself_response):
        """Test reading an unsupported resource type."""
        transport = MockTransport(
            {"/rest/api/3/myself": {"status_code": 200, "content": mock_myself_response}}
        )
        connector = JiraConnector(jira_config, transport=transport)
        connector.authenticate()

        with pytest.raises(ValueError, match="Unsupported resource type"):
            connector.read("unsupported_type")


class TestJiraConnectorWriteOperations:
    """Tests for Jira connector write operations."""

    def test_create_issue_success(self, mock_env, jira_config, mock_myself_response):
        transport = MockTransport(
            {
                "/rest/api/3/myself": {"status_code": 200, "content": mock_myself_response},
                "/rest/api/3/issue": {"status_code": 201, "content": {"id": "3000", "key": "TEST-1"}},
            }
        )
        connector = JiraConnector(jira_config, transport=transport)
        connector.authenticate()

        results = connector.write(
            "issues",
            [{"summary": "Write test", "project_key": "TEST", "issue_type": "Task"}],
        )

        assert results == [{"id": "3000", "key": "TEST-1", "status": None}]

    def test_update_issue_conflict(self, mock_env, jira_config, mock_myself_response):
        transport = MockTransport(
            {
                "/rest/api/3/myself": {"status_code": 200, "content": mock_myself_response},
                "/rest/api/3/issue/TEST-2": {
                    "status_code": 200,
                    "content": {
                        "id": "3001",
                        "key": "TEST-2",
                        "fields": {"updated": "2024-01-02T00:00:00Z"},
                    },
                },
            }
        )
        connector = JiraConnector(jira_config, transport=transport)
        connector.authenticate()

        results = connector.write(
            "issues",
            [{"key": "TEST-2", "status": "done", "updated_at": "2024-01-01T00:00:00Z"}],
        )

        assert results[0]["conflict"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
