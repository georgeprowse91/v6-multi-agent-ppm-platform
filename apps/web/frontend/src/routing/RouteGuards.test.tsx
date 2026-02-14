import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RequireAuth } from './RouteGuards';
import { useAppStore } from '@/store';

const resetStore = () => {
  useAppStore.setState({
    session: { authenticated: false, loading: true, user: null },
    tenantContext: { tenantId: null, tenantName: null },
    featureFlags: {},
  });
};

describe('RequireAuth', () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    resetStore();
  });

  it('bootstraps an authenticated session before rendering protected routes', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/v1/session')) {
        return Promise.resolve(new Response(JSON.stringify({
          authenticated: true,
          subject: 'demo-user',
          tenant_id: 'demo-tenant',
          roles: ['portfolio_admin'],
        }), { status: 200 }));
      }
      if (url.includes('/v1/api/roles')) {
        return Promise.resolve(new Response(JSON.stringify([
          {
            id: 'portfolio_admin',
            permissions: ['admin:access', 'portfolio.view'],
          },
        ]), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route element={<RequireAuth />}>
            <Route path="/" element={<div>Protected home</div>} />
          </Route>
          <Route path="/login" element={<div>Login</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Protected home')).toBeInTheDocument();

    await waitFor(() => {
      const state = useAppStore.getState();
      expect(state.session.loading).toBe(false);
      expect(state.session.authenticated).toBe(true);
      expect(state.session.user?.id).toBe('demo-user');
      expect(state.session.user?.permissions).toContain('portfolio.view');
      expect(state.session.user?.roles).toEqual(['portfolio_admin']);
      expect(state.tenantContext).toEqual({ tenantId: 'demo-tenant', tenantName: 'demo-tenant' });
    });

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(2);
    });
  });

  it('resolves loading and redirects to login when bootstrap returns unauthenticated', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ authenticated: false }), { status: 200 })
    );

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route element={<RequireAuth />}>
            <Route path="/" element={<div>Protected home</div>} />
          </Route>
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Login page')).toBeInTheDocument();

    await waitFor(() => {
      const state = useAppStore.getState();
      expect(state.session.loading).toBe(false);
      expect(state.session.authenticated).toBe(false);
      expect(state.session.user).toBeNull();
      expect(state.tenantContext).toEqual({ tenantId: null, tenantName: null });
    });

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });
    expect(fetchSpy.mock.calls[0]?.[0]).toBe('/v1/session');
  });
});
