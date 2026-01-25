"""Tests for component discovery utilities."""

from __future__ import annotations

from tools.component_runner import discover_agents, discover_connectors


def test_discover_agents_contains_known_agent() -> None:
    agents = discover_agents()
    names = {agent.name for agent in agents}
    assert "agent-10-schedule-planning" in names


def test_discover_connectors_contains_known_connector() -> None:
    connectors = discover_connectors()
    names = {connector.name for connector in connectors}
    assert "jira" in names
