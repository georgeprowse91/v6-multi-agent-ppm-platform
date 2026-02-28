"""
Tests for the Planview Connector.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CONNECTOR_SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
PLANVIEW_CONNECTOR_PATH = REPO_ROOT / "connectors" / "planview" / "src"
for path in (REPO_ROOT, CONNECTOR_SDK_PATH, PLANVIEW_CONNECTOR_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from base_connector import (
    ConnectionStatus,
    ConnectorCategory,
    ConnectorConfig,
    SyncDirection,
    SyncFrequency,
)
from planview_connector import PlanviewConnector


class MockTransport(httpx.BaseTransport):
    """Mock HTTP transport for testing."""

    def __init__(self, responses: dict[str, list[dict[str, Any]]]):
        self._responses = responses
        self._requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self._requests.append(request)
        url_path = request.url.path
        for path_pattern, response_list in self._responses.items():
            if path_pattern in url_path and response_list:
                response_data = response_list.pop(0)
                status_code = response_data.get("status_code", 200)
                content = response_data.get("content", {})
                return httpx.Response(status_code=status_code, json=content, request=request)
        return httpx.Response(status_code=404, json={"error": "Not found"}, request=request)

    @property
    def requests(self) -> list[httpx.Request]:
        return self._requests


class FakeTokenManager:
    def __init__(self, token: str = "token-1") -> None:
        self.access_token = token
        self.refresh_count = 0

    def get_access_token(self) -> str:
        return self.access_token

    def refresh(self) -> None:
        self.refresh_count += 1
        self.access_token = f"token-{self.refresh_count + 1}"


@pytest.fixture
def mock_env():
    env_vars = {
        "PLANVIEW_INSTANCE_URL": "https://planview.example.com",
        "PLANVIEW_CLIENT_ID": "client-id",
        "PLANVIEW_CLIENT_SECRET": "client-secret",
        "PLANVIEW_REFRESH_TOKEN": "refresh-token",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def planview_config():
    return ConnectorConfig(
        connector_id="planview",
        name="Planview",
        category=ConnectorCategory.PPM,
        enabled=True,
        sync_direction=SyncDirection.INBOUND,
        sync_frequency=SyncFrequency.DAILY,
        instance_url="https://planview.example.com",
    )


def test_authenticate_success(mock_env, planview_config):
    transport = MockTransport(
        {
            "/api/v1/projects": [
                {"status_code": 200, "content": {"items": [], "total": 0, "offset": 0}}
            ]
        }
    )
    token_manager = FakeTokenManager()
    connector = PlanviewConnector(planview_config, transport=transport, token_manager=token_manager)

    assert connector.authenticate() is True
    assert connector.is_authenticated is True


def test_test_connection_unauthorized(mock_env, planview_config):
    transport = MockTransport(
        {
            "/api/v1/projects": [
                {"status_code": 401, "content": {"error": "Unauthorized"}},
                {"status_code": 401, "content": {"error": "Unauthorized"}},
            ]
        }
    )
    token_manager = FakeTokenManager()
    connector = PlanviewConnector(planview_config, transport=transport, token_manager=token_manager)

    result = connector.test_connection()

    assert result.status == ConnectionStatus.UNAUTHORIZED
    assert "Invalid credentials" in result.message


def test_read_projects_success(mock_env, planview_config):
    transport = MockTransport(
        {
            "/api/v1/projects": [
                {"status_code": 200, "content": {"items": [], "total": 0, "offset": 0}},
                {
                    "status_code": 200,
                    "content": {
                        "items": [
                            {
                                "id": "proj-1",
                                "programId": "program-1",
                                "name": "Project One",
                                "status": "execution",
                                "startDate": "2024-01-01",
                                "endDate": "2024-06-30",
                                "owner": "owner@example.com",
                                "classification": "internal",
                                "createdAt": "2024-01-01T00:00:00Z",
                            }
                        ],
                        "total": 1,
                        "offset": 0,
                    },
                }
            ]
        }
    )
    token_manager = FakeTokenManager()
    connector = PlanviewConnector(planview_config, transport=transport, token_manager=token_manager)
    connector.authenticate()

    projects = connector.read("projects")

    assert len(projects) == 1
    assert projects[0]["id"] == "proj-1"
    assert projects[0]["program_id"] == "program-1"
    assert projects[0]["name"] == "Project One"


def test_token_refresh_on_unauthorized(mock_env, planview_config):
    transport = MockTransport(
        {
            "/api/v1/projects": [
                {"status_code": 401, "content": {"error": "Unauthorized"}},
                {"status_code": 200, "content": {"items": [], "total": 0, "offset": 0}},
            ]
        }
    )
    token_manager = FakeTokenManager()
    connector = PlanviewConnector(planview_config, transport=transport, token_manager=token_manager)

    connector.authenticate()

    assert token_manager.refresh_count == 1
    assert len(transport.requests) == 2
