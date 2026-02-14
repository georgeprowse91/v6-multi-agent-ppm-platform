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

  it('does not render an MCP standalone section', () => {
    render(
      <MemoryRouter>
        <MethodologyNav />
      </MemoryRouter>
    );

    expect(screen.queryByText(/MCP Standalone/i)).not.toBeInTheDocument();
  });
});
