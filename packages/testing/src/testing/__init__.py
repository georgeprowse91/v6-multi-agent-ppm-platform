"""Shared test utilities for the PPM platform.

Provides reusable fixtures, mock builders, and assertion helpers used
across unit, integration, and end-to-end test suites.
"""

from testing.assertions import (
    assert_datetime_recent,
    assert_error_response,
    assert_json_schema,
    assert_valid_uuid,
)
from testing.fixtures import (
    MockAzureOpenAI,
    MockDatabase,
    MockEventBus,
    MockRedis,
    MockStateStore,
)
from testing.mock_builders import (
    build_agent_run,
    build_auth_headers,
    build_demand,
    build_project,
    build_risk,
)

__all__ = [
    # Assertions
    "assert_datetime_recent",
    "assert_error_response",
    "assert_json_schema",
    "assert_valid_uuid",
    # Fixtures / Mocks
    "MockAzureOpenAI",
    "MockDatabase",
    "MockEventBus",
    "MockRedis",
    "MockStateStore",
    # Mock builders
    "build_agent_run",
    "build_auth_headers",
    "build_demand",
    "build_project",
    "build_risk",
]
