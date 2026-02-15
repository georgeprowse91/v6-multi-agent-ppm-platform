import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AgentProfilePage } from './AgentProfilePage';

describe('AgentProfilePage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders profile mappings and run preview result', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      if (url.endsWith('/agents/config')) {
        return Promise.resolve(new Response(JSON.stringify([
          {
            catalog_id: 'agent-1',
            agent_id: 'intent-router',
            display_name: 'Intent Router',
            description: 'Routes intent',
            category: 'core',
            enabled: true,
            capabilities: [],
            parameters: [],
          },
        ]), { status: 200 }));
      }
      if (url.endsWith('/api/agent-gallery/agents/intent-router')) {
        return Promise.resolve(new Response(JSON.stringify({
          agent_id: 'intent-router',
          name: 'Intent Router',
          purpose: 'Routes intent',
          capabilities: ['routing'],
          inputs: ['workspace_context'],
          outputs: ['decision'],
          templates_touched: [{
            template_id: 'tmp-1',
            template_name: 'Template A',
            lifecycle_events: ['generate'],
            methodology_nodes: [],
            run_modes: ['dag'],
          }],
          connectors_used: [{ connector_type: 'jira', system: 'Jira', category: 'delivery', objects: [] }],
          methodology_nodes_supported: [],
          run_modes: ['dag', 'demo-safe'],
        }), { status: 200 }));
      }
      if (url.endsWith('/api/agent-gallery/agents/intent-router/run-preview') && init?.method === 'POST') {
        return Promise.resolve(new Response(JSON.stringify({
          agent_id: 'intent-router',
          demo_safe: true,
          run_trace: { correlation_id: 'abc' },
          artifacts: [],
          connector_operations: [],
          status: 'completed',
        }), { status: 200 }));
      }
      return Promise.resolve(new Response('Not Found', { status: 404 }));
    });

    render(
      <MemoryRouter initialEntries={['/config/agents/intent-router']}>
        <Routes>
          <Route path="/config/agents/:agent_id" element={<AgentProfilePage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByRole('heading', { name: 'Intent Router', level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/Template A/)).toBeInTheDocument();
  });
});
