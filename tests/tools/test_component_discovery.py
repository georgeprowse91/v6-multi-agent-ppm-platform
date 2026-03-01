"""Tests for component discovery utilities."""

from __future__ import annotations

from agents.runtime.src.agent_catalog import AGENT_CATALOG
from tools.component_runner import discover_agents, discover_connectors


def test_discover_agents_contains_known_agent() -> None:
    agents = discover_agents()
    names = {agent.name for agent in agents}
    assert "schedule-planning-agent" in names


def test_discover_connectors_contains_known_connector() -> None:
    connectors = discover_connectors()
    names = {connector.name for connector in connectors}
    assert "jira" in names


def test_agent_catalog_matches_component_discovery() -> None:
    agents = discover_agents()
    discovered = {agent.name for agent in agents}
    catalog_components = {entry.component_name for entry in AGENT_CATALOG}
    catalog_ids = {entry.catalog_id for entry in AGENT_CATALOG}
    agent_ids = {entry.agent_id for entry in AGENT_CATALOG}

    assert len(AGENT_CATALOG) == 25
    assert catalog_components.issubset(discovered)
    assert len(catalog_ids) == len(AGENT_CATALOG)
    assert len(agent_ids) == len(AGENT_CATALOG)
