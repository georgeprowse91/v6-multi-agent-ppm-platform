from integrations.connectors.integration.framework import (
    ConnectorRegistry,
    IntegrationAuthType,
    IntegrationConfig,
    JiraConnector,
    MockIntegrationConnector,
    default_registry,
)


def test_connector_registry_creates_connector():
    registry = ConnectorRegistry()
    registry.register(JiraConnector.system_name, JiraConnector)

    config = IntegrationConfig(
        system="jira",
        base_url="https://example.atlassian.net",
        auth_type=IntegrationAuthType.API_KEY,
        api_key="token",
    )
    connector = registry.create("jira", config)

    assert connector.authenticate() is True


def test_default_registry_lists_systems():
    registry = default_registry()
    systems = registry.list_systems()

    assert "jira" in systems


def test_default_registry_uses_mock_connectors_in_demo_mode(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    registry = default_registry()

    config = IntegrationConfig(system="jira", base_url="https://demo.local", auth_type=IntegrationAuthType.NONE)
    connector = registry.create("jira", config)

    assert isinstance(connector, MockIntegrationConnector)
