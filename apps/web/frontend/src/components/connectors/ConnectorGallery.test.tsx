import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConnectorGallery } from './ConnectorGallery';
import { useConnectorStore } from '@/store/connectors';
import { useAppStore } from '@/store';

const mockConnectors = [
  {
    connector_id: 'jira',
    name: 'Jira',
    description: 'Atlassian Jira connector',
    category: 'pm',
    status: 'production',
    icon: 'jira',
    supported_sync_directions: ['inbound'],
    auth_type: 'api_key',
    config_fields: [],
    env_vars: [],
    enabled: false,
    configured: true,
    instance_url: 'https://jira.example.com',
    project_key: 'PPM',
    sync_direction: 'inbound',
    sync_frequency: 'daily',
    health_status: 'healthy',
    last_sync_at: null,
    certification_status: 'certified',
  },
];

const mockCertifications = [
  {
    connector_id: 'jira',
    tenant_id: 'tenant-alpha',
    compliance_status: 'certified',
    certification_date: '2024-10-01',
    expires_at: null,
    audit_reference: 'SOC2-2024-10',
    notes: null,
    documents: [],
    updated_at: '2024-10-02T00:00:00Z',
    updated_by: 'qa-user',
  },
];

describe('ConnectorGallery', () => {
  afterEach(() => {
    vi.restoreAllMocks();
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
    });
  });

  it('renders certification status from the API', async () => {
    useAppStore.setState({
      session: {
        authenticated: true,
        loading: false,
        user: {
          id: 'user-1',
          name: 'User',
          email: 'user@example.com',
          tenantId: 'tenant-alpha',
          roles: ['portfolio_admin'],
          permissions: ['config.manage'],
        },
      },
    });

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo) => {
      const url = typeof input === 'string' ? input : input.url;
      if (url.endsWith('/connectors')) {
        return Promise.resolve(new Response(JSON.stringify(mockConnectors), { status: 200 }));
      }
      if (url.endsWith('/connectors/categories')) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      }
      if (url.endsWith('/certifications')) {
        return Promise.resolve(new Response(JSON.stringify(mockCertifications), { status: 200 }));
      }
      return Promise.resolve(new Response('Not Found', { status: 404 }));
    });

    render(<ConnectorGallery />);

    expect(await screen.findByText('Certified')).toBeInTheDocument();
  });

  it('enables MCP tool mapping and reflects MCP state in the summary', async () => {
    const updateConnectorConfig = vi.fn().mockResolvedValue(undefined);
    const mockConnector = {
      ...mockConnectors[0],
      supported_operations: ['projects.read', 'projects.write'],
      connector_type: 'rest',
      mcp_server_id: null,
      mcp_server_url: null,
      mcp_tool_map: null,
      mcp_scopes: [],
    };

    useAppStore.setState({
      session: {
        authenticated: true,
        loading: false,
        user: {
          id: 'user-1',
          name: 'User',
          email: 'user@example.com',
          tenantId: 'tenant-alpha',
          roles: ['portfolio_admin'],
          permissions: ['config.manage'],
        },
      },
    });

    useConnectorStore.setState({
      connectors: [mockConnector],
      connectorsLoading: false,
      connectorsError: null,
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
      fetchConnectors: vi.fn(),
      fetchCategories: vi.fn(),
      fetchCertifications: vi.fn(),
      getFilteredConnectors: () => useConnectorStore.getState().connectors,
      openConnectorModal: (connector) =>
        useConnectorStore.setState({ selectedConnector: connector, isModalOpen: true }),
      closeConnectorModal: () => useConnectorStore.setState({ selectedConnector: null, isModalOpen: false }),
      updateConnectorConfig,
      testConnection: vi.fn().mockResolvedValue({ status: 'success', message: 'ok' }),
      clearTestResult: vi.fn(),
    });

    render(<ConnectorGallery />);

    fireEvent.click(screen.getByRole('button', { name: 'Configure' }));

    const integrationSelect = screen.getByDisplayValue('REST');
    fireEvent.change(integrationSelect, { target: { value: 'mcp' } });

    expect(screen.getByText('MCP Server')).toBeInTheDocument();

    const summarySection = screen.getByText('Configuration Summary').parentElement;
    expect(summarySection).not.toBeNull();
    expect(within(summarySection as HTMLElement).getByText('MCP')).toBeInTheDocument();

    const comboBoxes = screen.getAllByRole('combobox');
    const mcpServerSelect = comboBoxes[1];
    const mcpToolSelect = comboBoxes[2];

    fireEvent.change(mcpServerSelect, { target: { value: 'mcp-core' } });
    fireEvent.change(screen.getByPlaceholderText('https://mcp.example.com'), {
      target: { value: 'https://mcp.internal' },
    });
    fireEvent.change(mcpToolSelect, { target: { value: 'projects.write' } });

    fireEvent.click(screen.getByRole('button', { name: 'Save Configuration' }));

    await waitFor(() => {
      expect(updateConnectorConfig).toHaveBeenCalledWith(
        'jira',
        expect.objectContaining({
          connector_type: 'mcp',
          mcp_server_id: 'mcp-core',
          mcp_server_url: 'https://mcp.internal',
          mcp_tool_map: { 'projects.write': true },
        })
      );
    });
  });

  it('uses project-level config updates and hides MCP fields for REST', async () => {
    const updateProjectConnectorConfig = vi.fn().mockResolvedValue(undefined);
    const projectConnector = {
      ...mockConnectors[0],
      connector_type: 'mcp',
      supported_operations: ['projects.read', 'projects.write'],
      mcp_server_id: 'mcp-core',
      mcp_server_url: 'https://mcp.example.com',
      mcp_tool_map: { 'projects.read': true },
      mcp_scopes: ['projects:read'],
    };

    useAppStore.setState({
      session: {
        authenticated: true,
        loading: false,
        user: {
          id: 'user-1',
          name: 'User',
          email: 'user@example.com',
          tenantId: 'tenant-alpha',
          roles: ['portfolio_admin'],
          permissions: ['config.manage'],
        },
      },
    });

    useConnectorStore.setState({
      connectors: [],
      connectorsLoading: false,
      connectorsError: null,
      projectConnectors: { 'project-1': [projectConnector] },
      projectConnectorsLoading: { 'project-1': false },
      projectConnectorsError: { 'project-1': null },
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
      fetchProjectConnectors: vi.fn(),
      fetchCategories: vi.fn(),
      fetchCertifications: vi.fn(),
      getFilteredProjectConnectors: (projectId) =>
        useConnectorStore.getState().projectConnectors[projectId] || [],
      openConnectorModal: (connector) =>
        useConnectorStore.setState({ selectedConnector: connector, isModalOpen: true }),
      closeConnectorModal: () => useConnectorStore.setState({ selectedConnector: null, isModalOpen: false }),
      updateProjectConnectorConfig,
      testProjectConnection: vi.fn().mockResolvedValue({ status: 'success', message: 'ok' }),
      clearTestResult: vi.fn(),
    });

    render(<ConnectorGallery projectId="project-1" />);

    fireEvent.click(screen.getByRole('button', { name: 'Configure' }));

    const integrationSelect = screen.getByDisplayValue('MCP');
    fireEvent.change(integrationSelect, { target: { value: 'rest' } });

    expect(screen.queryByText('MCP Server URL')).not.toBeInTheDocument();

    const summarySection = screen.getByText('Configuration Summary').parentElement;
    expect(summarySection).not.toBeNull();
    expect(within(summarySection as HTMLElement).getByText('REST')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Save Configuration' }));

    await waitFor(() => {
      expect(updateProjectConnectorConfig).toHaveBeenCalledWith(
        'project-1',
        'jira',
        expect.objectContaining({
          connector_type: 'rest',
          mcp_server_id: undefined,
          mcp_server_url: undefined,
          mcp_tool_map: undefined,
          mcp_scopes: undefined,
        })
      );
    });
  });
});
