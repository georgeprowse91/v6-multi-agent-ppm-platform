import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/i18n';
import { AppLayout } from './AppLayout';
import { allPermissionIds } from '@/auth/permissions';
import { useAppStore } from '@/store';
import { ThemeProvider } from '@/components/theme/ThemeProvider';

vi.mock('shepherd.js', () => ({
  default: {
    Tour: class {
      addStep = vi.fn();
      start = vi.fn();
      on = vi.fn();
    },
  },
}));

const resetStore = () => {
  useAppStore.setState({
    session: { authenticated: false, loading: true, user: null },
    tenantContext: { tenantId: null, tenantName: null },
    featureFlags: {},
  });
};

describe('AppLayout', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    resetStore();
  });

  it('renders the assistant panel in the layout', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ authenticated: false }), { status: 200 }))
    );
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      value: vi.fn(),
      writable: true,
    });

    render(
      <I18nProvider>
        <ThemeProvider>
          <MemoryRouter>
            <AppLayout>
              <div>Workspace</div>
            </AppLayout>
          </MemoryRouter>
        </ThemeProvider>
      </I18nProvider>
    );

    expect(await screen.findByRole('heading', { name: 'Assistant' })).toBeInTheDocument();
  });

  it('keeps full permissions when roles API fails for authenticated sessions', async () => {
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
        return Promise.resolve(new Response('error', { status: 500 }));
      }
      if (url.includes('/v1/config')) {
        return Promise.resolve(new Response(JSON.stringify({ feature_flags: {} }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    render(
      <I18nProvider>
        <ThemeProvider>
          <MemoryRouter>
            <AppLayout>
              <div>Workspace</div>
            </AppLayout>
          </MemoryRouter>
        </ThemeProvider>
      </I18nProvider>
    );

    await screen.findByRole('heading', { name: 'Assistant' });

    await waitFor(() => {
      const session = useAppStore.getState().session;
      expect(session.authenticated).toBe(true);
      expect(session.user?.permissions).toEqual(allPermissionIds());
    });

    expect(fetchSpy).toHaveBeenCalled();
  });

  it('uses full permissions when role resolution returns none', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/v1/session')) {
        return Promise.resolve(new Response(JSON.stringify({
          authenticated: true,
          subject: 'demo-user',
          tenant_id: 'demo-tenant',
          roles: ['unknown_role'],
        }), { status: 200 }));
      }
      if (url.includes('/v1/api/roles')) {
        return Promise.resolve(new Response(JSON.stringify([{
          id: 'PMO_ADMIN',
          permissions: ['roles.manage'],
        }]), { status: 200 }));
      }
      if (url.includes('/v1/config')) {
        return Promise.resolve(new Response(JSON.stringify({ feature_flags: {} }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    render(
      <I18nProvider>
        <ThemeProvider>
          <MemoryRouter>
            <AppLayout>
              <div>Workspace</div>
            </AppLayout>
          </MemoryRouter>
        </ThemeProvider>
      </I18nProvider>
    );

    await waitFor(() => {
      expect(useAppStore.getState().session.user?.permissions).toEqual(allPermissionIds());
    });
  });
});
