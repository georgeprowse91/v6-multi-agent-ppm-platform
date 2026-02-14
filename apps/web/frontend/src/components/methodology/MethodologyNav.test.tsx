import { render, screen } from '@testing-library/react';
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
});
