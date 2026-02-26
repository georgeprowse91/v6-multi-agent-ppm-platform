import { describe, expect, it, beforeEach, vi } from 'vitest';
import { useConnectorStore } from './useConnectorStore';
import type { Connector, ConnectorFilterState } from './types';

// Mock global fetch for API calls
global.fetch = vi.fn();

/** Helper to build a minimal Connector object for testing. */
function makeConnector(overrides: Partial<Connector> = {}): Connector {
  return {
    connector_id: 'test-connector',
    name: 'Test Connector',
    description: 'A test connector',
    category: 'pm',
    system: 'test',
    connector_type: 'rest',
    mcp_server_id: '',
    supported_operations: [],
    mcp_preferred: false,
    status: 'beta',
    icon: 'test',
    supported_sync_directions: ['inbound'],
    auth_type: 'api_key',
    config_fields: [],
    env_vars: [],
    supported_objects: [],
    limitations: [],
    auth_requirements: [],
    enabled: false,
    configured: false,
    instance_url: '',
    project_key: '',
    sync_direction: 'inbound',
    sync_frequency: 'daily',
    health_status: 'unknown',
    last_sync_at: null,
    ...overrides,
  };
}

describe('useConnectorStore', () => {
  beforeEach(() => {
    // Reset store data between tests - do NOT use replace (true) which strips action functions
    useConnectorStore.setState({
      connectors: [],
      connectorsLoading: false,
      connectorsError: null,
      projectConnectors: {},
      projectConnectorsLoading: {},
      projectConnectorsError: {},
      categories: [],
      categoriesLoading: false,
      certifications: {},
      certificationsLoading: false,
      certificationsError: null,
      filter: {
        search: '',
        category: 'all',
        statusFilter: 'all',
        certificationFilter: 'all',
        enabledOnly: false,
      },
      selectedConnector: null,
      isModalOpen: false,
      testingConnection: false,
      testResult: null,
      mcpToolsBySystem: {},
      mcpToolsLoading: {},
      mcpToolsError: {},
    });
    vi.resetAllMocks();
  });

  describe('initial state', () => {
    it('should have empty connectors array', () => {
      const state = useConnectorStore.getState();
      expect(state.connectors).toEqual([]);
    });

    it('should have loading flags set to false', () => {
      const state = useConnectorStore.getState();
      expect(state.connectorsLoading).toBe(false);
      expect(state.categoriesLoading).toBe(false);
      expect(state.certificationsLoading).toBe(false);
      expect(state.testingConnection).toBe(false);
    });

    it('should have null error states', () => {
      const state = useConnectorStore.getState();
      expect(state.connectorsError).toBeNull();
      expect(state.certificationsError).toBeNull();
    });

    it('should have default filter state', () => {
      const state = useConnectorStore.getState();
      expect(state.filter).toEqual({
        search: '',
        category: 'all',
        statusFilter: 'all',
        certificationFilter: 'all',
        enabledOnly: false,
      });
    });

    it('should have modal closed and no selected connector', () => {
      const state = useConnectorStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.selectedConnector).toBeNull();
      expect(state.testResult).toBeNull();
    });
  });

  describe('fetchConnectors', () => {
    it('should set loading state while fetching', async () => {
      const mockResponse = new Response(JSON.stringify([]), { status: 200 });
      vi.mocked(fetch).mockResolvedValue(mockResponse);

      const fetchPromise = useConnectorStore.getState().fetchConnectors();
      // Loading should be true after calling
      expect(useConnectorStore.getState().connectorsLoading).toBe(true);

      await fetchPromise;
      expect(useConnectorStore.getState().connectorsLoading).toBe(false);
    });

    it('should set error when API response is not ok', async () => {
      const mockResponse = new Response(null, { status: 500, statusText: 'Internal Server Error' });
      vi.mocked(fetch).mockResolvedValue(mockResponse);

      await useConnectorStore.getState().fetchConnectors();

      const state = useConnectorStore.getState();
      expect(state.connectorsError).toBe('Failed to fetch connectors: Internal Server Error');
      expect(state.connectorsLoading).toBe(false);
    });

    it('should set error and stop loading when fetch throws', async () => {
      vi.mocked(fetch).mockRejectedValue(new Error('Network error'));

      await useConnectorStore.getState().fetchConnectors();

      const state = useConnectorStore.getState();
      expect(state.connectorsError).toBe('Network error');
      expect(state.connectorsLoading).toBe(false);
    });

    it('should populate connectors on successful response', async () => {
      const mockConnectors = [
        { connector_id: 'jira', name: 'Jira', description: 'Jira PM', category: 'pm', enabled: false },
      ];
      const mockResponse = new Response(JSON.stringify(mockConnectors), { status: 200 });
      vi.mocked(fetch).mockResolvedValue(mockResponse);

      await useConnectorStore.getState().fetchConnectors();

      const state = useConnectorStore.getState();
      expect(state.connectors.length).toBe(1);
      expect(state.connectors[0].connector_id).toBe('jira');
      expect(state.connectorsLoading).toBe(false);
      expect(state.connectorsError).toBeNull();
    });
  });

  describe('filter actions', () => {
    it('should update filter with setFilter', () => {
      useConnectorStore.getState().setFilter({ search: 'jira' });

      const state = useConnectorStore.getState();
      expect(state.filter.search).toBe('jira');
      // Other filter values remain unchanged
      expect(state.filter.category).toBe('all');
    });

    it('should update certification filter with setCertificationFilter', () => {
      useConnectorStore.getState().setCertificationFilter('certified');

      const state = useConnectorStore.getState();
      expect(state.filter.certificationFilter).toBe('certified');
    });

    it('should reset filter to defaults', () => {
      useConnectorStore.getState().setFilter({ search: 'test', category: 'pm', enabledOnly: true });
      useConnectorStore.getState().resetFilter();

      const state = useConnectorStore.getState();
      expect(state.filter).toEqual({
        search: '',
        category: 'all',
        statusFilter: 'all',
        certificationFilter: 'all',
        enabledOnly: false,
      });
    });

    it('should filter connectors by search term', () => {
      useConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', name: 'Jira', description: 'Jira PM' }),
          makeConnector({ connector_id: 'slack', name: 'Slack', description: 'Messaging' }),
        ],
      });

      useConnectorStore.getState().setFilter({ search: 'jira' });
      const filtered = useConnectorStore.getState().getFilteredConnectors();
      expect(filtered.length).toBe(1);
      expect(filtered[0].connector_id).toBe('jira');
    });

    it('should filter connectors by category', () => {
      useConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', name: 'Jira', category: 'pm' }),
          makeConnector({ connector_id: 'slack', name: 'Slack', category: 'collaboration' }),
        ],
      });

      useConnectorStore.getState().setFilter({ category: 'collaboration' });
      const filtered = useConnectorStore.getState().getFilteredConnectors();
      expect(filtered.length).toBe(1);
      expect(filtered[0].connector_id).toBe('slack');
    });

    it('should filter connectors by enabledOnly', () => {
      useConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', name: 'Jira', enabled: true }),
          makeConnector({ connector_id: 'slack', name: 'Slack', enabled: false }),
        ],
      });

      useConnectorStore.getState().setFilter({ enabledOnly: true });
      const filtered = useConnectorStore.getState().getFilteredConnectors();
      expect(filtered.length).toBe(1);
      expect(filtered[0].connector_id).toBe('jira');
    });
  });

  describe('modal actions', () => {
    it('should open the connector modal', () => {
      const connector = makeConnector({ connector_id: 'jira', name: 'Jira' });
      useConnectorStore.getState().openConnectorModal(connector);

      const state = useConnectorStore.getState();
      expect(state.isModalOpen).toBe(true);
      expect(state.selectedConnector?.connector_id).toBe('jira');
      expect(state.testResult).toBeNull();
    });

    it('should close the connector modal and clear state', () => {
      const connector = makeConnector({ connector_id: 'jira', name: 'Jira' });
      useConnectorStore.getState().openConnectorModal(connector);
      useConnectorStore.getState().closeConnectorModal();

      const state = useConnectorStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.selectedConnector).toBeNull();
      expect(state.testResult).toBeNull();
    });
  });

  describe('getConnector and helper selectors', () => {
    it('should find a connector by ID', () => {
      useConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', name: 'Jira' }),
          makeConnector({ connector_id: 'slack', name: 'Slack' }),
        ],
      });

      const jira = useConnectorStore.getState().getConnector('jira');
      expect(jira?.name).toBe('Jira');
    });

    it('should return undefined for unknown connector ID', () => {
      useConnectorStore.setState({
        connectors: [makeConnector({ connector_id: 'jira', name: 'Jira' })],
      });

      const unknown = useConnectorStore.getState().getConnector('nonexistent');
      expect(unknown).toBeUndefined();
    });

    it('should get connectors by category', () => {
      useConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', category: 'pm' }),
          makeConnector({ connector_id: 'azure', category: 'pm' }),
          makeConnector({ connector_id: 'slack', category: 'collaboration' }),
        ],
      });

      const pmConnectors = useConnectorStore.getState().getConnectorsByCategory('pm');
      expect(pmConnectors.length).toBe(2);
    });

    it('should get enabled connector for a category', () => {
      useConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', category: 'pm', enabled: false }),
          makeConnector({ connector_id: 'azure', category: 'pm', enabled: true }),
        ],
      });

      const enabled = useConnectorStore.getState().getEnabledConnectorForCategory('pm');
      expect(enabled?.connector_id).toBe('azure');
    });
  });

  describe('testConnection', () => {
    it('should set testingConnection to true during test and false after', async () => {
      const testResult = {
        status: 'connected',
        message: 'OK',
        details: {},
        tested_at: '2026-01-01T00:00:00Z',
      };
      // For the test POST call
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response(JSON.stringify(testResult), { status: 200 })
      );
      // For the subsequent fetchConnectors call (since status === connected)
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response(JSON.stringify([]), { status: 200 })
      );

      const promise = useConnectorStore.getState().testConnection('jira');
      expect(useConnectorStore.getState().testingConnection).toBe(true);

      const result = await promise;
      expect(useConnectorStore.getState().testingConnection).toBe(false);
      expect(result.status).toBe('connected');
      expect(useConnectorStore.getState().testResult?.status).toBe('connected');
    });

    it('should handle connection test failure', async () => {
      vi.mocked(fetch).mockRejectedValue(new Error('Connection refused'));

      const result = await useConnectorStore.getState().testConnection('jira');

      expect(result.status).toBe('failed');
      expect(result.message).toBe('Connection refused');
      expect(useConnectorStore.getState().testingConnection).toBe(false);
    });
  });

  describe('clearTestResult', () => {
    it('should clear the test result', () => {
      useConnectorStore.setState({
        testResult: {
          status: 'connected',
          message: 'OK',
          details: {},
          tested_at: '2026-01-01T00:00:00Z',
        },
      });

      useConnectorStore.getState().clearTestResult();
      expect(useConnectorStore.getState().testResult).toBeNull();
    });
  });

  describe('applyTemplateConnectors', () => {
    it('should enable and disable connectors based on template config', () => {
      useConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', category: 'pm', enabled: false }),
          makeConnector({ connector_id: 'slack', category: 'collaboration', enabled: true }),
        ],
      });

      useConnectorStore.getState().applyTemplateConnectors({
        enabled: ['jira'],
        disabled: ['slack'],
      });

      const state = useConnectorStore.getState();
      const jira = state.connectors.find((c) => c.connector_id === 'jira');
      const slack = state.connectors.find((c) => c.connector_id === 'slack');
      expect(jira?.enabled).toBe(true);
      expect(slack?.enabled).toBe(false);
    });
  });
});
