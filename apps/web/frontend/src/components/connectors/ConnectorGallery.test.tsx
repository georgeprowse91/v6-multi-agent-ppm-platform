import { render, screen } from '@testing-library/react';
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
});
