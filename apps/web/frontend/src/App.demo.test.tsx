import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DemoHomeRedirect } from './App';
import { useAppStore } from '@/store';

vi.mock('./pages/HomePage', () => ({
  default: () => <div>Home page</div>,
}));

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{`${location.pathname}${location.search}`}</div>;
}

describe('DemoHomeRedirect', () => {
  beforeEach(() => {
    useAppStore.setState({
      session: { authenticated: false, loading: false, user: null },
      tenantContext: { tenantId: null, tenantName: null },
      featureFlags: {},
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('redirects root route to seeded demo project when demo mode is enabled and user is authenticated', async () => {
    vi.stubEnv('VITE_DEMO_MODE', 'true');
    useAppStore.setState({
      session: {
        authenticated: true,
        loading: false,
        user: {
          id: 'demo-user',
          name: 'Demo User',
          email: 'demo@example.com',
          tenantId: 'demo-tenant',
          roles: ['PMO_ADMIN'],
          permissions: ['portfolio.view'],
        },
      },
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<><DemoHomeRedirect /><LocationProbe /></>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByTestId('location')).toHaveTextContent('/?project_id=demo-predictive');
  });
});
