import { describe, expect, it, beforeEach, vi } from 'vitest';
import { useProjectConnectorStore } from './useProjectConnectorStore';
import type { Connector, ConnectorFilterState } from '@/store/connectors/types';

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

const DEFAULT_FILTER: ConnectorFilterState = {
  search: '',
  category: 'all',
  statusFilter: 'all',
  certificationFilter: 'all',
  enabledOnly: false,
};

describe('useProjectConnectorStore', () => {
  beforeEach(() => {
    // Reset data fields only - do NOT use replace (true) which strips action functions
    useProjectConnectorStore.setState({
      projectId: null,
      connectors: [],
      connectorsLoading: false,
      connectorsError: null,
      categories: [],
      categoriesLoading: false,
      certifications: {},
      certificationsLoading: false,
      certificationsError: null,
      filter: { ...DEFAULT_FILTER },
      selectedConnector: null,
      isModalOpen: false,
      testingConnection: false,
      testResult: null,
    });
    vi.resetAllMocks();
  });

  describe('initial state', () => {
    it('should have null projectId', () => {
      expect(useProjectConnectorStore.getState().projectId).toBeNull();
    });

    it('should have empty connectors array', () => {
      expect(useProjectConnectorStore.getState().connectors).toEqual([]);
    });

    it('should have loading flags set to false', () => {
      const state = useProjectConnectorStore.getState();
      expect(state.connectorsLoading).toBe(false);
      expect(state.categoriesLoading).toBe(false);
      expect(state.certificationsLoading).toBe(false);
      expect(state.testingConnection).toBe(false);
    });

    it('should have default filter state', () => {
      expect(useProjectConnectorStore.getState().filter).toEqual(DEFAULT_FILTER);
    });

    it('should have modal closed', () => {
      const state = useProjectConnectorStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.selectedConnector).toBeNull();
    });
  });

  describe('setProjectId', () => {
    it('should set the project ID', () => {
      useProjectConnectorStore.getState().setProjectId('project-123');
      expect(useProjectConnectorStore.getState().projectId).toBe('project-123');
    });

    it('should allow changing the project ID', () => {
      useProjectConnectorStore.getState().setProjectId('project-123');
      useProjectConnectorStore.getState().setProjectId('project-456');
      expect(useProjectConnectorStore.getState().projectId).toBe('project-456');
    });
  });

  describe('fetchConnectors', () => {
    it('should not fetch when projectId is null', async () => {
      await useProjectConnectorStore.getState().fetchConnectors();

      expect(fetch).not.toHaveBeenCalled();
      expect(useProjectConnectorStore.getState().connectorsLoading).toBe(false);
    });

    it('should set loading state while fetching', async () => {
      useProjectConnectorStore.getState().setProjectId('proj-1');
      const mockResponse = new Response(JSON.stringify([]), { status: 200 });
      vi.mocked(fetch).mockResolvedValue(mockResponse);

      const promise = useProjectConnectorStore.getState().fetchConnectors();
      expect(useProjectConnectorStore.getState().connectorsLoading).toBe(true);

      await promise;
      expect(useProjectConnectorStore.getState().connectorsLoading).toBe(false);
    });

    it('should set error when API returns a non-ok response', async () => {
      useProjectConnectorStore.getState().setProjectId('proj-1');
      const mockResponse = new Response(null, { status: 500, statusText: 'Internal Server Error' });
      vi.mocked(fetch).mockResolvedValue(mockResponse);

      await useProjectConnectorStore.getState().fetchConnectors();

      const state = useProjectConnectorStore.getState();
      expect(state.connectorsError).toBe('Failed to fetch connectors: Internal Server Error');
      expect(state.connectorsLoading).toBe(false);
    });

    it('should populate connectors on success', async () => {
      useProjectConnectorStore.getState().setProjectId('proj-1');
      const mockConnectors = [
        { connector_id: 'jira', name: 'Jira', description: 'PM', category: 'pm', enabled: true },
      ];
      vi.mocked(fetch).mockResolvedValue(
        new Response(JSON.stringify(mockConnectors), { status: 200 })
      );

      await useProjectConnectorStore.getState().fetchConnectors();

      const state = useProjectConnectorStore.getState();
      expect(state.connectors.length).toBe(1);
      expect(state.connectors[0].connector_id).toBe('jira');
      expect(state.connectorsLoading).toBe(false);
    });

    it('should call the correct project-scoped endpoint', async () => {
      useProjectConnectorStore.getState().setProjectId('my-project');
      vi.mocked(fetch).mockResolvedValue(
        new Response(JSON.stringify([]), { status: 200 })
      );

      await useProjectConnectorStore.getState().fetchConnectors();

      expect(fetch).toHaveBeenCalledWith('/api/projects/my-project/connectors');
    });
  });

  describe('filter actions', () => {
    it('should update filter with setFilter', () => {
      useProjectConnectorStore.getState().setFilter({ search: 'slack' });

      const state = useProjectConnectorStore.getState();
      expect(state.filter.search).toBe('slack');
      expect(state.filter.category).toBe('all');
    });

    it('should reset filter to defaults', () => {
      useProjectConnectorStore.getState().setFilter({ search: 'test', category: 'pm' });
      useProjectConnectorStore.getState().resetFilter();

      expect(useProjectConnectorStore.getState().filter).toEqual(DEFAULT_FILTER);
    });

    it('should filter connectors by search term', () => {
      useProjectConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', name: 'Jira', description: 'PM tool' }),
          makeConnector({ connector_id: 'slack', name: 'Slack', description: 'Messaging' }),
        ],
      });

      useProjectConnectorStore.getState().setFilter({ search: 'slack' });
      const filtered = useProjectConnectorStore.getState().getFilteredConnectors();
      expect(filtered.length).toBe(1);
      expect(filtered[0].connector_id).toBe('slack');
    });

    it('should filter connectors by category', () => {
      useProjectConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', category: 'pm' }),
          makeConnector({ connector_id: 'slack', category: 'collaboration' }),
        ],
      });

      useProjectConnectorStore.getState().setFilter({ category: 'pm' });
      const filtered = useProjectConnectorStore.getState().getFilteredConnectors();
      expect(filtered.length).toBe(1);
      expect(filtered[0].connector_id).toBe('jira');
    });

    it('should filter connectors by enabledOnly', () => {
      useProjectConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', enabled: true }),
          makeConnector({ connector_id: 'slack', enabled: false }),
        ],
      });

      useProjectConnectorStore.getState().setFilter({ enabledOnly: true });
      const filtered = useProjectConnectorStore.getState().getFilteredConnectors();
      expect(filtered.length).toBe(1);
      expect(filtered[0].connector_id).toBe('jira');
    });
  });

  describe('modal actions', () => {
    it('should open the connector modal', () => {
      const connector = makeConnector({ connector_id: 'jira', name: 'Jira' });
      useProjectConnectorStore.getState().openConnectorModal(connector);

      const state = useProjectConnectorStore.getState();
      expect(state.isModalOpen).toBe(true);
      expect(state.selectedConnector?.connector_id).toBe('jira');
      expect(state.testResult).toBeNull();
    });

    it('should close the connector modal', () => {
      const connector = makeConnector({ connector_id: 'jira' });
      useProjectConnectorStore.getState().openConnectorModal(connector);
      useProjectConnectorStore.getState().closeConnectorModal();

      const state = useProjectConnectorStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.selectedConnector).toBeNull();
    });
  });

  describe('getConnector', () => {
    it('should find a connector by ID', () => {
      useProjectConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', name: 'Jira' }),
          makeConnector({ connector_id: 'slack', name: 'Slack' }),
        ],
      });

      const jira = useProjectConnectorStore.getState().getConnector('jira');
      expect(jira?.name).toBe('Jira');
    });

    it('should return undefined for unknown connector', () => {
      useProjectConnectorStore.setState({
        connectors: [makeConnector({ connector_id: 'jira' })],
      });

      expect(useProjectConnectorStore.getState().getConnector('nonexistent')).toBeUndefined();
    });
  });

  describe('getConnectorsByCategory and getEnabledConnectorForCategory', () => {
    beforeEach(() => {
      useProjectConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', category: 'pm', enabled: false }),
          makeConnector({ connector_id: 'azure', category: 'pm', enabled: true }),
          makeConnector({ connector_id: 'slack', category: 'collaboration', enabled: true }),
        ],
      });
    });

    it('should get connectors by category', () => {
      const pm = useProjectConnectorStore.getState().getConnectorsByCategory('pm');
      expect(pm.length).toBe(2);
    });

    it('should get the enabled connector for a category', () => {
      const enabled = useProjectConnectorStore.getState().getEnabledConnectorForCategory('pm');
      expect(enabled?.connector_id).toBe('azure');
    });

    it('should return undefined when no connector is enabled in category', () => {
      const enabled = useProjectConnectorStore.getState().getEnabledConnectorForCategory('erp');
      expect(enabled).toBeUndefined();
    });
  });

  describe('testConnection', () => {
    it('should return invalid_config when projectId is null', async () => {
      const result = await useProjectConnectorStore.getState().testConnection('jira');

      expect(result.status).toBe('invalid_config');
      expect(result.message).toBe('Missing project context');
    });

    it('should set testingConnection to true during test', async () => {
      useProjectConnectorStore.getState().setProjectId('proj-1');
      const testResult = {
        status: 'connected',
        message: 'OK',
        details: {},
        tested_at: '2026-01-01T00:00:00Z',
      };
      // For test POST call
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response(JSON.stringify(testResult), { status: 200 })
      );
      // For subsequent fetchConnectors (on success)
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response(JSON.stringify([]), { status: 200 })
      );

      const promise = useProjectConnectorStore.getState().testConnection('jira');
      expect(useProjectConnectorStore.getState().testingConnection).toBe(true);

      const result = await promise;
      expect(useProjectConnectorStore.getState().testingConnection).toBe(false);
      expect(result.status).toBe('connected');
    });

    it('should handle fetch failure gracefully', async () => {
      useProjectConnectorStore.getState().setProjectId('proj-1');
      vi.mocked(fetch).mockRejectedValue(new Error('Network error'));

      const result = await useProjectConnectorStore.getState().testConnection('jira');

      expect(result.status).toBe('failed');
      expect(result.message).toBe('Network error');
      expect(useProjectConnectorStore.getState().testingConnection).toBe(false);
    });
  });

  describe('clearTestResult', () => {
    it('should clear the test result', () => {
      useProjectConnectorStore.setState({
        testResult: {
          status: 'connected',
          message: 'OK',
          details: {},
          tested_at: '2026-01-01T00:00:00Z',
        },
      });

      useProjectConnectorStore.getState().clearTestResult();
      expect(useProjectConnectorStore.getState().testResult).toBeNull();
    });
  });

  describe('applyTemplateConnectors', () => {
    it('should enable connectors from template and enforce category mutual exclusivity', () => {
      useProjectConnectorStore.setState({
        connectors: [
          makeConnector({ connector_id: 'jira', category: 'pm', enabled: false }),
          makeConnector({ connector_id: 'azure', category: 'pm', enabled: false }),
          makeConnector({ connector_id: 'slack', category: 'collaboration', enabled: true }),
        ],
      });

      useProjectConnectorStore.getState().applyTemplateConnectors({
        enabled: ['jira', 'azure'],
        disabled: ['slack'],
      });

      const state = useProjectConnectorStore.getState();
      // Category mutual exclusivity: only first pm connector stays enabled
      const jira = state.connectors.find((c) => c.connector_id === 'jira');
      const azure = state.connectors.find((c) => c.connector_id === 'azure');
      const slack = state.connectors.find((c) => c.connector_id === 'slack');

      expect(jira?.enabled).toBe(true);
      // azure is also pm category but jira got there first, so azure is disabled
      expect(azure?.enabled).toBe(false);
      expect(slack?.enabled).toBe(false);
    });
  });
});
