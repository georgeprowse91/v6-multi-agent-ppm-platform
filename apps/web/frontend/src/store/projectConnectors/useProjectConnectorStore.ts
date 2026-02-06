/**
 * Project Connector Store
 *
 * Zustand store for managing project-scoped connector configurations,
 * connection testing, and category-based filtering.
 */

import { create } from 'zustand';
import type {
  CategoryInfo,
  CertificationRecord,
  Connector,
  ConnectorCategory,
  ConnectorConfigUpdate,
  ConnectorFilterState,
  ConnectionTestResult,
} from '@/store/connectors/types';

// API base URL for shared resources (certifications)
const API_BASE = '/v1';
const PROJECT_API_BASE = '/api/projects';

interface ProjectConnectorStoreState {
  projectId: string | null;
  setProjectId: (projectId: string) => void;
  // Connectors
  connectors: Connector[];
  connectorsLoading: boolean;
  connectorsError: string | null;

  // Categories
  categories: CategoryInfo[];
  categoriesLoading: boolean;

  // Certifications
  certifications: Record<string, CertificationRecord>;
  certificationsLoading: boolean;
  certificationsError: string | null;

  // Filter state
  filter: ConnectorFilterState;

  // Selected connector for modal
  selectedConnector: Connector | null;
  isModalOpen: boolean;

  // Connection testing
  testingConnection: boolean;
  testResult: ConnectionTestResult | null;

  // Actions - Connectors
  fetchConnectors: () => Promise<void>;
  fetchCategories: () => Promise<void>;
  fetchCertifications: () => Promise<void>;
  getConnector: (connectorId: string) => Connector | undefined;
  getCertification: (connectorId: string) => CertificationRecord | undefined;
  updateConnectorConfig: (connectorId: string, config: ConnectorConfigUpdate) => Promise<void>;
  enableConnector: (connectorId: string) => Promise<void>;
  disableConnector: (connectorId: string) => Promise<void>;
  updateCertification: (
    connectorId: string,
    payload: Partial<Omit<CertificationRecord, 'connector_id' | 'tenant_id' | 'documents' | 'updated_at'>>
  ) => Promise<CertificationRecord | null>;
  uploadCertificationDocument: (
    connectorId: string,
    file: File,
    uploadedBy?: string
  ) => Promise<CertificationRecord | null>;

  // Actions - Connection Testing
  testConnection: (connectorId: string, instanceUrl?: string, projectKey?: string) => Promise<ConnectionTestResult>;
  clearTestResult: () => void;

  // Actions - Filter
  setFilter: (filter: Partial<ConnectorFilterState>) => void;
  resetFilter: () => void;
  getFilteredConnectors: () => Connector[];

  // Actions - Modal
  openConnectorModal: (connector: Connector) => void;
  closeConnectorModal: () => void;

  // Helpers
  getConnectorsByCategory: (category: ConnectorCategory) => Connector[];
  getEnabledConnectorForCategory: (category: ConnectorCategory) => Connector | undefined;

  // Template application
  applyTemplateConnectors: (config: { enabled: string[]; disabled: string[] }) => void;
}

const DEFAULT_FILTER: ConnectorFilterState = {
  search: '',
  category: 'all',
  statusFilter: 'all',
  enabledOnly: false,
};

const getProjectBase = (projectId: string | null) => {
  if (!projectId) return null;
  return `${PROJECT_API_BASE}/${projectId}`;
};

export const useProjectConnectorStore = create<ProjectConnectorStoreState>((set, get) => ({
  // Initial state
  projectId: null,
  connectors: [],
  connectorsLoading: false,
  connectorsError: null,
  categories: [],
  categoriesLoading: false,
  certifications: {},
  certificationsLoading: false,
  certificationsError: null,
  filter: DEFAULT_FILTER,
  selectedConnector: null,
  isModalOpen: false,
  testingConnection: false,
  testResult: null,

  setProjectId: (projectId) => {
    set({ projectId });
  },

  // Fetch all connectors
  fetchConnectors: async () => {
    set({ connectorsLoading: true, connectorsError: null });
    try {
      const base = getProjectBase(get().projectId);
      if (!base) {
        set({ connectorsLoading: false });
        return;
      }
      const response = await fetch(`${base}/connectors`);
      if (!response.ok) {
        const message = `Failed to fetch connectors: ${response.statusText}`;
        set({ connectorsError: message, connectorsLoading: false });
        return;
      }
      const data = await response.json();
      set({ connectors: data, connectorsLoading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      set({ connectorsError: message, connectorsLoading: false });
      // Fall back to mock data only when the API is unreachable
      if (error instanceof TypeError && message.includes('Failed to fetch')) {
        set({ connectors: getMockConnectors() });
      }
    }
  },

  // Fetch categories
  fetchCategories: async () => {
    set({ categoriesLoading: true });
    const base = getProjectBase(get().projectId);
    if (!base) {
      set({ categoriesLoading: false, categories: getDefaultCategories() });
      return;
    }
    try {
      const response = await fetch(`${base}/connectors/categories`);
      if (!response.ok) {
        throw new Error(`Failed to fetch categories: ${response.statusText}`);
      }
      const data = await response.json();
      set({ categories: data, categoriesLoading: false });
    } catch (error) {
      set({ categoriesLoading: false });
      // Use default categories
      set({ categories: getDefaultCategories() });
    }
  },

  fetchCertifications: async () => {
    set({ certificationsLoading: true, certificationsError: null });
    try {
      const response = await fetch(`${API_BASE}/certifications`);
      if (!response.ok) {
        throw new Error(`Failed to fetch certifications: ${response.statusText}`);
      }
      const data = (await response.json()) as CertificationRecord[];
      const mapped = data.reduce<Record<string, CertificationRecord>>((acc, record) => {
        acc[record.connector_id] = record;
        return acc;
      }, {});
      set({ certifications: mapped, certificationsLoading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      set({ certificationsError: message, certificationsLoading: false });
    }
  },

  // Get a specific connector
  getConnector: (connectorId) => {
    return get().connectors.find((c) => c.connector_id === connectorId);
  },

  getCertification: (connectorId) => {
    return get().certifications[connectorId];
  },

  // Update connector configuration
  updateConnectorConfig: async (connectorId, config) => {
    const base = getProjectBase(get().projectId);
    if (!base) return;
    try {
      const response = await fetch(`${base}/connectors/${connectorId}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (!response.ok) {
        throw new Error(`Failed to update connector: ${response.statusText}`);
      }
      // Refresh connectors
      await get().fetchConnectors();
    } catch (error) {
      // Update locally for development
      set((state) => ({
        connectors: state.connectors.map((c) =>
          c.connector_id === connectorId
            ? {
                ...c,
                ...config,
                configured: true,
              }
            : c
        ),
      }));
    }
  },

  updateCertification: async (connectorId, payload) => {
    try {
      const response = await fetch(`${API_BASE}/certifications/${connectorId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Failed to update certification: ${response.statusText}`);
      }
      const record = (await response.json()) as CertificationRecord;
      set((state) => ({
        certifications: { ...state.certifications, [connectorId]: record },
      }));
      return record;
    } catch (error) {
      return null;
    }
  },

  uploadCertificationDocument: async (connectorId, file, uploadedBy) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (uploadedBy) {
        formData.append('uploaded_by', uploadedBy);
      }
      const response = await fetch(`${API_BASE}/certifications/${connectorId}/documents`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error(`Failed to upload certification evidence: ${response.statusText}`);
      }
      const record = (await response.json()) as CertificationRecord;
      set((state) => ({
        certifications: { ...state.certifications, [connectorId]: record },
      }));
      return record;
    } catch (error) {
      return null;
    }
  },

  // Enable a connector (disables others in same category)
  enableConnector: async (connectorId) => {
    const base = getProjectBase(get().projectId);
    if (!base) return;
    try {
      const response = await fetch(`${base}/connectors/${connectorId}/enable`, {
        method: 'POST',
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to enable connector: ${response.statusText}`);
      }
      // Refresh connectors
      await get().fetchConnectors();
    } catch (error) {
      // Update locally for development with mutual exclusivity
      const connector = get().getConnector(connectorId);
      if (!connector) return;

      set((state) => ({
        connectors: state.connectors.map((c) => {
          if (c.connector_id === connectorId) {
            return { ...c, enabled: true };
          }
          // Disable others in same category
          if (c.category === connector.category && c.enabled) {
            return { ...c, enabled: false };
          }
          return c;
        }),
      }));
    }
  },

  // Disable a connector
  disableConnector: async (connectorId) => {
    const base = getProjectBase(get().projectId);
    if (!base) return;
    try {
      const response = await fetch(`${base}/connectors/${connectorId}/disable`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`Failed to disable connector: ${response.statusText}`);
      }
      // Refresh connectors
      await get().fetchConnectors();
    } catch (error) {
      // Update locally for development
      set((state) => ({
        connectors: state.connectors.map((c) =>
          c.connector_id === connectorId ? { ...c, enabled: false } : c
        ),
      }));
    }
  },

  // Test connection
  testConnection: async (connectorId, instanceUrl, projectKey) => {
    set({ testingConnection: true, testResult: null });
    const base = getProjectBase(get().projectId);
    if (!base) {
      set({ testingConnection: false });
      return { status: 'invalid_config', message: 'Missing project context', details: {}, tested_at: '' };
    }
    try {
      const response = await fetch(`${base}/connectors/${connectorId}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instance_url: instanceUrl || '',
          project_key: projectKey || '',
        }),
      });

      const result: ConnectionTestResult = await response.json();
      set({ testResult: result, testingConnection: false });

      // If connection was successful, refresh connectors to get updated health status
      if (result.status === 'connected') {
        await get().fetchConnectors();
      }

      return result;
    } catch (error) {
      const result: ConnectionTestResult = {
        status: 'failed',
        message: error instanceof Error ? error.message : 'Connection test failed',
        details: {},
        tested_at: new Date().toISOString(),
      };
      set({ testResult: result, testingConnection: false });
      return result;
    }
  },

  // Clear test result
  clearTestResult: () => {
    set({ testResult: null });
  },

  // Set filter
  setFilter: (filter) => {
    set((state) => ({
      filter: { ...state.filter, ...filter },
    }));
  },

  // Reset filter
  resetFilter: () => {
    set({ filter: DEFAULT_FILTER });
  },

  // Get filtered connectors
  getFilteredConnectors: () => {
    const { connectors, filter } = get();
    let filtered = [...connectors];

    // Apply search filter
    if (filter.search) {
      const search = filter.search.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.name.toLowerCase().includes(search) ||
          c.description.toLowerCase().includes(search) ||
          c.connector_id.toLowerCase().includes(search)
      );
    }

    // Apply category filter
    if (filter.category !== 'all') {
      filtered = filtered.filter((c) => c.category === filter.category);
    }

    // Apply status filter
    if (filter.statusFilter !== 'all') {
      filtered = filtered.filter((c) => c.status === filter.statusFilter);
    }

    // Apply enabled filter
    if (filter.enabledOnly) {
      filtered = filtered.filter((c) => c.enabled);
    }

    return filtered;
  },

  // Open connector modal
  openConnectorModal: (connector) => {
    set({ selectedConnector: connector, isModalOpen: true, testResult: null });
  },

  // Close connector modal
  closeConnectorModal: () => {
    set({ selectedConnector: null, isModalOpen: false, testResult: null });
  },

  applyTemplateConnectors: (config) => {
    set((state) => {
      const enabledSet = new Set(config.enabled);
      const disabledSet = new Set(config.disabled);
      const baseConnectors =
        state.connectors.length > 0 ? state.connectors : getMockConnectors();

      const updated = baseConnectors.map((connector) => {
        if (enabledSet.has(connector.connector_id)) {
          return { ...connector, enabled: true };
        }
        if (disabledSet.has(connector.connector_id)) {
          return { ...connector, enabled: false };
        }
        return connector;
      });

      const seenCategories = new Set<ConnectorCategory>();
      const normalized = updated.map((connector) => {
        if (!connector.enabled) return connector;
        if (seenCategories.has(connector.category)) {
          return { ...connector, enabled: false };
        }
        seenCategories.add(connector.category);
        return connector;
      });

      return { connectors: normalized };
    });
  },

  // Get connectors by category
  getConnectorsByCategory: (category) => {
    return get().connectors.filter((c) => c.category === category);
  },

  // Get enabled connector for a category
  getEnabledConnectorForCategory: (category) => {
    return get().connectors.find((c) => c.category === category && c.enabled);
  },
}));

/**
 * Mock connectors for development when API is not available
 */
function getMockConnectors(): Connector[] {
  return [
    // PM Tools
    {
      connector_id: 'jira',
      name: 'Jira',
      description: 'Atlassian Jira for agile project tracking and issue management',
      category: 'pm',
      status: 'production',
      icon: 'jira',
      supported_sync_directions: ['inbound'],
      auth_type: 'api_key',
      config_fields: [
        { name: 'instance_url', type: 'url', required: true, label: 'Instance URL' },
        { name: 'project_key', type: 'string', required: false, label: 'Project Key' },
      ],
      env_vars: ['JIRA_INSTANCE_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN'],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'inbound',
      sync_frequency: 'daily',
      health_status: 'unknown',
      last_sync_at: null,
    },
    {
      connector_id: 'azure_devops',
      name: 'Azure DevOps',
      description: 'Microsoft Azure DevOps for source control, CI/CD, and work tracking',
      category: 'pm',
      status: 'beta',
      icon: 'azure',
      supported_sync_directions: ['inbound', 'bidirectional'],
      auth_type: 'api_key',
      config_fields: [],
      env_vars: ['AZURE_DEVOPS_ORG_URL', 'AZURE_DEVOPS_PAT'],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'inbound',
      sync_frequency: 'daily',
      health_status: 'unknown',
      last_sync_at: null,
    },
    // PPM Tools
    {
      connector_id: 'planview',
      name: 'Planview',
      description: 'Enterprise PPM platform for portfolio and resource management',
      category: 'ppm',
      status: 'beta',
      icon: 'planview',
      supported_sync_directions: ['inbound', 'bidirectional'],
      auth_type: 'api_key',
      config_fields: [],
      env_vars: ['PLANVIEW_API_URL', 'PLANVIEW_API_TOKEN'],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'inbound',
      sync_frequency: 'daily',
      health_status: 'unknown',
      last_sync_at: null,
    },
    // Collaboration
    {
      connector_id: 'slack',
      name: 'Slack',
      description: 'Slack for team messaging and collaboration',
      category: 'collaboration',
      status: 'beta',
      icon: 'slack',
      supported_sync_directions: ['outbound', 'bidirectional'],
      auth_type: 'api_key',
      config_fields: [
        { name: 'slack_bot_token', type: 'string', required: true, label: 'Bot Token' },
        { name: 'slack_signing_secret', type: 'string', required: true, label: 'Signing Secret' },
        { name: 'default_channel', type: 'string', required: false, label: 'Default Channel' },
      ],
      env_vars: ['SLACK_API_URL', 'SLACK_BOT_TOKEN', 'SLACK_SIGNING_SECRET'],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'outbound',
      sync_frequency: 'realtime',
      health_status: 'unknown',
      last_sync_at: null,
      custom_fields: {
        slack_bot_token: '',
        slack_signing_secret: '',
        default_channel: '',
      },
    },
    {
      connector_id: 'teams',
      name: 'Microsoft Teams',
      description: 'Microsoft Teams for collaboration and communication',
      category: 'collaboration',
      status: 'beta',
      icon: 'teams',
      supported_sync_directions: ['outbound', 'bidirectional'],
      auth_type: 'oauth2',
      config_fields: [],
      env_vars: ['TEAMS_TENANT_ID', 'TEAMS_CLIENT_ID', 'TEAMS_CLIENT_SECRET'],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'outbound',
      sync_frequency: 'realtime',
      health_status: 'unknown',
      last_sync_at: null,
    },
    // Document Management
    {
      connector_id: 'sharepoint',
      name: 'SharePoint',
      description: 'Microsoft SharePoint for document management and collaboration',
      category: 'doc_mgmt',
      status: 'beta',
      icon: 'sharepoint',
      supported_sync_directions: ['inbound', 'bidirectional'],
      auth_type: 'oauth2',
      config_fields: [],
      env_vars: ['SHAREPOINT_TENANT_ID', 'SHAREPOINT_CLIENT_ID', 'SHAREPOINT_CLIENT_SECRET'],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'inbound',
      sync_frequency: 'daily',
      health_status: 'unknown',
      last_sync_at: null,
    },
    // ERP
    {
      connector_id: 'sap',
      name: 'SAP',
      description: 'SAP ERP for enterprise resource planning and financials',
      category: 'erp',
      status: 'beta',
      icon: 'sap',
      supported_sync_directions: ['inbound'],
      auth_type: 'basic',
      config_fields: [],
      env_vars: ['SAP_URL', 'SAP_USERNAME', 'SAP_PASSWORD', 'SAP_CLIENT'],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'inbound',
      sync_frequency: 'daily',
      health_status: 'unknown',
      last_sync_at: null,
    },
    // HRIS
    {
      connector_id: 'workday',
      name: 'Workday',
      description: 'Workday HCM for human capital management',
      category: 'hris',
      status: 'beta',
      icon: 'workday',
      supported_sync_directions: ['inbound'],
      auth_type: 'oauth2',
      config_fields: [
        { name: 'tenant', type: 'string', required: true, label: 'Tenant' },
        { name: 'client_id', type: 'string', required: true, label: 'Client ID' },
        { name: 'client_secret', type: 'string', required: true, label: 'Client Secret' },
        { name: 'refresh_token', type: 'string', required: true, label: 'Refresh Token' },
        { name: 'token_url', type: 'url', required: false, label: 'Token URL' },
      ],
      env_vars: [
        'WORKDAY_API_URL',
        'WORKDAY_CLIENT_ID',
        'WORKDAY_CLIENT_SECRET',
        'WORKDAY_REFRESH_TOKEN',
        'WORKDAY_TOKEN_URL',
      ],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'inbound',
      sync_frequency: 'daily',
      health_status: 'unknown',
      last_sync_at: null,
      custom_fields: {
        tenant: '',
        client_id: '',
        client_secret: '',
        refresh_token: '',
        token_url: '',
      },
    },
    // GRC
    {
      connector_id: 'servicenow_grc',
      name: 'ServiceNow GRC',
      description: 'ServiceNow Governance, Risk, and Compliance',
      category: 'grc',
      status: 'beta',
      icon: 'servicenow',
      supported_sync_directions: ['inbound', 'bidirectional'],
      auth_type: 'oauth2',
      config_fields: [],
      env_vars: ['SERVICENOW_URL', 'SERVICENOW_CLIENT_ID', 'SERVICENOW_CLIENT_SECRET'],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'inbound',
      sync_frequency: 'daily',
      health_status: 'unknown',
      last_sync_at: null,
    },
    // Compliance
    {
      connector_id: 'regulatory_compliance',
      name: 'Regulatory Compliance',
      description: 'Regulatory compliance APIs for HIPAA and FDA CFR 21 Part 11 audit trails',
      category: 'compliance',
      status: 'beta',
      icon: 'shield-check',
      supported_sync_directions: ['inbound', 'outbound'],
      auth_type: 'api_key',
      config_fields: [
        { name: 'endpoint_url', type: 'url', required: true, label: 'Compliance API Endpoint' },
        { name: 'api_key', type: 'string', required: true, label: 'API Key' },
        { name: 'supported_regulations', type: 'string', required: false, label: 'Supported Regulations (comma-separated)' },
      ],
      env_vars: ['REGULATORY_COMPLIANCE_ENDPOINT', 'REGULATORY_COMPLIANCE_API_KEY'],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'inbound',
      sync_frequency: 'daily',
      health_status: 'unknown',
      last_sync_at: null,
    },
    // IoT Integrations
    {
      connector_id: 'iot',
      name: 'IoT Integrations',
      description: 'Custom hardware and sensor integrations via device endpoints',
      category: 'iot',
      status: 'coming_soon',
      icon: 'cpu-chip',
      supported_sync_directions: ['inbound', 'outbound'],
      auth_type: 'api_key',
      config_fields: [
        { name: 'device_endpoint', type: 'url', required: true, label: 'Device Endpoint' },
        { name: 'auth_token', type: 'string', required: true, label: 'Auth Token' },
        { name: 'sensor_types', type: 'string', required: false, label: 'Supported Sensor Types' },
      ],
      env_vars: ['IOT_DEVICE_ENDPOINT', 'IOT_AUTH_TOKEN'],
      enabled: false,
      configured: false,
      instance_url: '',
      project_key: '',
      sync_direction: 'inbound',
      sync_frequency: 'realtime',
      health_status: 'unknown',
      last_sync_at: null,
      custom_fields: {
        device_endpoint: '',
        auth_token: '',
        sensor_types: '',
      },
    },
  ];
}

/**
 * Default categories for development
 */
function getDefaultCategories(): CategoryInfo[] {
  return [
    { value: 'ppm', label: 'PPM Tools', icon: 'domain.portfolio', description: 'Portfolio and Project Management platforms', connector_count: 3, enabled_connector: null },
    { value: 'pm', label: 'PM Tools', icon: 'provenance.auditLog', description: 'Project management and work tracking tools', connector_count: 4, enabled_connector: null },
    { value: 'doc_mgmt', label: 'Document Management', icon: 'artifact.folder', description: 'Document storage and collaboration platforms', connector_count: 3, enabled_connector: null },
    { value: 'erp', label: 'ERP Systems', icon: 'domain.platform', description: 'Enterprise resource planning systems', connector_count: 3, enabled_connector: null },
    { value: 'hris', label: 'HRIS', icon: 'communication.user', description: 'Human resource information systems', connector_count: 3, enabled_connector: null },
    { value: 'collaboration', label: 'Collaboration', icon: 'communication.message', description: 'Team communication and collaboration tools', connector_count: 3, enabled_connector: null },
    { value: 'grc', label: 'GRC', icon: 'domain.governance', description: 'Governance, Risk, and Compliance platforms', connector_count: 3, enabled_connector: null },
    { value: 'compliance', label: 'Compliance', icon: 'domain.governance', description: 'Specialised regulatory compliance platforms', connector_count: 1, enabled_connector: null },
    { value: 'iot', label: 'IoT Integrations', icon: 'connectors.cpuChip', description: 'Custom hardware and sensor integrations', connector_count: 1, enabled_connector: null },
  ];
}

export default useProjectConnectorStore;
