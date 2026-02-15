import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import EnterpriseUpliftPage from './EnterpriseUpliftPage';

const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input);
  if (url.includes('/demand')) return new Response(JSON.stringify({ items: [{ id: 'd1', title: 'Demand One', status: 'intake' }] }));
  if (url.includes('/prioritisation/score')) return new Response(JSON.stringify({ results: [{ id: 'd1', score: 8.4 }] }));
  if (url.includes('/scenarios/compare')) return new Response(JSON.stringify({ scenarios: [{ id: 's1', name: 'Balanced', value_score: 80, budget: 1000 }] }));
  if (url.includes('/scenarios/s1/publish') && init?.method === 'POST') return new Response(JSON.stringify({ status: 'published' }));
  return new Response(JSON.stringify({}), { status: 200 });
});

describe('EnterpriseUpliftPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockClear();
  });

  it('renders demand board and scenario compare, supports publish', async () => {
    render(<MemoryRouter><EnterpriseUpliftPage /></MemoryRouter>);
    await screen.findByRole('table', { name: 'Demand board table' });
    fireEvent.click(screen.getByRole('radio'));
    fireEvent.click(screen.getByRole('button', { name: 'Publish decision' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/scenarios/s1/publish'), expect.objectContaining({ method: 'POST' })));
  });

  it('toggles table and kanban views', async () => {
    render(<MemoryRouter><EnterpriseUpliftPage /></MemoryRouter>);
    await screen.findByRole('table', { name: 'Demand board table' });
    fireEvent.click(screen.getByRole('button', { name: /Toggle Kanban/i }));
    expect(screen.getByLabelText('Demand board kanban')).toBeInTheDocument();
  });
});
