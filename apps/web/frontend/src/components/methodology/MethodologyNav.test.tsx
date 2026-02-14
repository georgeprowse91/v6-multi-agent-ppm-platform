import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMethodologyStore } from '@/store/methodology';
import { MethodologyNav } from './MethodologyNav';

vi.mock('@/components/icon/Icon', () => ({
  Icon: ({ label }: { label?: string }) => <span>{label ?? 'icon'}</span>,
}));

describe('MethodologyNav', () => {
  beforeEach(() => {
    useMethodologyStore.setState((state) => ({
      ...state,
      currentActivityId: null,
      expandedStageIds: ['stage-1'],
      projectMethodology: {
        projectId: 'demo-project',
        projectName: 'Demo Project',
        currentActivityId: null,
        expandedStageIds: ['stage-1'],
        methodology: {
          id: 'predictive',
          name: 'Predictive',
          description: 'Test methodology',
          type: 'predictive',
          version: 'test',
          stages: [
            {
              id: 'stage-1',
              name: 'Stage 1',
              status: 'not_started',
              prerequisites: [],
              order: 1,
              activities: [
                { id: 'activity-1', name: 'Activity 1', status: 'not_started', canvasType: 'document', prerequisites: [], order: 1 },
              ],
            },
          ],
          monitoring: [
            { id: 'monitor-1', name: 'Project Performance & Insights Dashboard', status: 'not_started', canvasType: 'dashboard', prerequisites: [], order: 1, alwaysAccessible: true },
          ],
        },
      },
    }));
  });

  it('renders compact stage/activity navigation', () => {
    render(<MemoryRouter><MethodologyNav /></MemoryRouter>);
    expect(screen.getAllByRole('button').length).toBeGreaterThan(0);
    expect(screen.queryByText('Template Runtime Mapping')).not.toBeInTheDocument();
    expect(screen.getByText(/Monitoring & Controlling/i)).toBeInTheDocument();
  });

  it('selects activity and resolves runtime view without opening artifact', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/api/workspace/') && url.includes('/select')) {
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      }
      if (url.includes('/api/methodology/runtime/resolve')) {
        return new Response(JSON.stringify({ resolution_contract: { canvas: { canvas_type: 'document', renderer_component: 'DocumentCanvas', default_view: 'edit' } } }), { status: 200 });
      }
      if (url.includes('/api/methodology/runtime/actions')) {
        return new Response(JSON.stringify({ actions: ['view'] }), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });
    vi.stubGlobal('fetch', fetchMock);

    useMethodologyStore.setState((state) => ({
      ...state,
      expandedStageIds: ['stage-1'],
      projectMethodology: {
        ...state.projectMethodology,
        methodology: {
          ...state.projectMethodology.methodology,
          stages: [{ ...state.projectMethodology.methodology.stages[0], activities: [{ id: 'activity-runtime-test', name: 'Runtime Test Activity', status: 'not_started', canvasType: 'document', prerequisites: [], order: 1 }] }],
        },
      },
    }));

    render(<MemoryRouter><MethodologyNav /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: /Runtime Test Activity/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/workspace/'), expect.objectContaining({ method: 'POST' }));
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/methodology/runtime/resolve'), undefined);
    });
  });
});
