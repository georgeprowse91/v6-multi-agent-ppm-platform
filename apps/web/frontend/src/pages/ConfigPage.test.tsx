import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConfigPage } from './ConfigPage';

const mockAgents = [
  {
    catalog_id: 'agent-1',
    agent_id: 'intent-router',
    display_name: 'Intent Router',
    description: 'Routes user intent.',
    category: 'core',
    enabled: true,
    capabilities: [],
    parameters: [
      {
        name: 'threshold',
        display_name: 'Threshold',
        description: 'Confidence threshold',
        param_type: 'number',
        default_value: 0.5,
        current_value: 0.6,
        required: true,
        options: [],
      },
    ],
  },
];

const mockConnectors = [
  {
    connector_id: 'connector-1',
    name: 'Jira',
    description: 'Jira connector',
    category: 'pm',
    system: 'Jira',
    connector_type: 'rest',
    mcp_server_id: '',
    supported_operations: ['issues.read'],
    mcp_preferred: false,
    status: 'available',
    icon: 'jira',
    supported_sync_directions: ['inbound'],
    auth_type: 'token',
    config_fields: [
      {
        name: 'api_token',
        type: 'string',
        required: true,
        label: 'API Token',
      },
    ],
    env_vars: [],
    supported_objects: ['issues'],
    limitations: [],
    auth_requirements: ['api_key'],
    enabled: true,
    configured: true,
    instance_url: 'https://jira.example.com',
    project_key: 'PPM',
    sync_direction: 'inbound',
    sync_frequency: 'daily',
    health_status: 'healthy',
    last_sync_at: null,
  },
];

const mockWorkflowConfig = {
  default_routing: [
    {
      agent_id: 'response-orchestration',
      action: 'route',
      intent: 'portfolio_intake',
      priority: 1,
      depends_on: ['intent-router'],
    },
  ],
  last_updated_by: 'system',
};

describe('ConfigPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders configuration tabs and agent forms', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: string | URL | Request) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      if (url.endsWith('/agents/config')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockAgents), { status: 200 })
        );
      }
      if (url.endsWith('/connectors')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockConnectors), { status: 200 })
        );
      }
      if (url.endsWith('/orchestration/config')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockWorkflowConfig), { status: 200 })
        );
      }
      return Promise.resolve(new Response('Not found', { status: 404 }));
    });

    render(<ConfigPage type="agents" />);

    expect(await screen.findByText('Intent Router')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Agents' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(screen.getByRole('tab', { name: 'Connectors' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Workflows' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Configure' }));
    expect(screen.getByLabelText(/Threshold/)).toBeInTheDocument();
  });
});
