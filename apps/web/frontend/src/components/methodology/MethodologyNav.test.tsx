import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useMethodologyStore } from '@/store/methodology';
import { MethodologyNav } from './MethodologyNav';

vi.mock('@/components/icon/Icon', () => ({
  Icon: ({ label }: { label?: string }) => <span>{label ?? 'icon'}</span>,
}));

describe('MethodologyNav', () => {
  afterEach(() => {
    useMethodologyStore.getState().createFromTemplate('methodology-predictive', 'project-demo', 'Project Apollo');
  });

  it('renders methodology tree for project workspace context', () => {
    render(
      <MemoryRouter>
        <MethodologyNav />
      </MemoryRouter>
    );

    expect(screen.getByRole('navigation', { name: 'Methodology navigation' })).toBeInTheDocument();
    expect(screen.getByText('Project')).toBeInTheDocument();
    expect(screen.getByText('Project Apollo')).toBeInTheDocument();
    expect(screen.getByText('Initiation')).toBeInTheDocument();
  });



  it('renders template runtime mappings grouped by lifecycle event', () => {
    useMethodologyStore.setState({
      templatesAvailableHere: [
        {
          template_id: 'adaptive-software-dev',
          name: 'Adaptive Software Dev',
          version: 1,
          methodology_bindings: [
            {
              methodology_id: 'adaptive',
              stage_id: '0.5-iteration-sprint-delivery-repeating-cycle',
              activity_id: useMethodologyStore.getState().projectMethodology.methodology.stages[0]?.activities[0]?.id ?? 'fallback-activity',
              task_id: null,
              lifecycle_events: ['generate'],
              required: false,
              gate_refs: [],
            },
          ],
          canvas_binding: { canvas_type: 'document', renderer_component: 'DocumentCanvas', default_view: 'edit' },
        },
      ],
    });

    render(
      <MemoryRouter>
        <MethodologyNav />
      </MemoryRouter>
    );

    expect(screen.getByText('Template Runtime Mapping')).toBeInTheDocument();
    expect(screen.getByText('GENERATE')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Adaptive Software Dev' })).toBeInTheDocument();
  });

  it('does not render an MCP standalone section', () => {
    render(
      <MemoryRouter>
        <MethodologyNav />
      </MemoryRouter>
    );

    expect(screen.queryByText(/MCP Standalone/i)).not.toBeInTheDocument();
  });



  it('triggers node action via backend runtime action endpoint', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/api/methodology/runtime/actions')) {
        return new Response(JSON.stringify({ actions: ['view', 'generate'] }), { status: 200 });
      }
      if (url.includes('/api/methodology/runtime/resolve')) {
        return new Response(
          JSON.stringify({
            resolution_contract: {
              canvas: {
                canvas_type: 'document',
                renderer_component: 'DocumentCanvas',
                default_view: 'preview',
              },
            },
          }),
          { status: 200 }
        );
      }
      if (url.includes('/api/methodology/runtime/action')) {
        return new Response(JSON.stringify({ status: 'completed', assistant_response: { content: 'ok', output_format: 'markdown' } }), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    vi.stubGlobal('fetch', fetchMock);
    useMethodologyStore.setState((state) => ({
      currentActivityId: 'activity-runtime-test',
      templatesAvailableHere: [
        {
          template_id: 'adaptive-software-dev',
          name: 'Adaptive Software Dev',
          version: 1,
          methodology_bindings: [
            {
              methodology_id: 'adaptive',
              stage_id: state.projectMethodology.methodology.stages[0]?.id ?? 'stage-1',
              activity_id: 'activity-runtime-test',
              task_id: null,
              lifecycle_events: ['generate'],
              required: false,
              gate_refs: [],
            },
          ],
          canvas_binding: { canvas_type: 'document', renderer_component: 'DocumentCanvas', default_view: 'edit' },
        },
      ],
      runtimeActionsAvailable: ['view', 'generate'],
      backendReachable: true,
      projectMethodology: {
        ...state.projectMethodology,
        methodology: {
          ...state.projectMethodology.methodology,
          stages: state.projectMethodology.methodology.stages.map((stage, index) => (
            index === 0
              ? {
                  ...stage,
                  activities: [
                    {
                      id: 'activity-runtime-test',
                      name: 'Runtime Test Activity',
                      description: 'Activity for runtime resolution testing',
                      status: 'not_started',
                      canvasType: 'document',
                      prerequisites: [],
                      order: 1,
                    },
                  ],
                }
              : stage
          )),
        },
      },
    }));

    render(
      <MemoryRouter>
        <MethodologyNav />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /Runtime Test Activity/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Adaptive Software Dev' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/methodology/runtime/action',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  it('resolves node runtime on activity click and uses resolved renderer contract path', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/api/methodology/runtime/actions')) {
        return new Response(JSON.stringify({ actions: ['view', 'generate'] }), { status: 200 });
      }
      if (url.includes('/api/methodology/runtime/resolve')) {
        return new Response(
          JSON.stringify({
            resolution_contract: {
              canvas: {
                canvas_type: 'document',
                renderer_component: 'DocumentCanvas',
                default_view: 'preview',
              },
            },
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    vi.stubGlobal('fetch', fetchMock);
    useMethodologyStore.setState((state) => ({
      projectMethodology: {
        ...state.projectMethodology,
        methodology: {
          ...state.projectMethodology.methodology,
          stages: state.projectMethodology.methodology.stages.map((stage, index) => (
            index === 0
              ? {
                  ...stage,
                  activities: [
                    {
                      id: 'activity-runtime-test',
                      name: 'Runtime Test Activity',
                      description: 'Activity for runtime resolution testing',
                      status: 'not_started',
                      canvasType: 'document',
                      prerequisites: [],
                      order: 1,
                    },
                  ],
                }
              : stage
          )),
        },
      },
    }));

    render(
      <MemoryRouter>
        <MethodologyNav />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /Runtime Test Activity/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/methodology/runtime/actions'), undefined);
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/methodology/runtime/resolve'), undefined);
    });
  });
});
