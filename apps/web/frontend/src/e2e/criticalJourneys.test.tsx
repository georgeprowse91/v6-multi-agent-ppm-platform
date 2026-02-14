import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '@/App';
import { useAppStore } from '@/store';
import { I18nProvider } from '@/i18n';
import { ThemeProvider } from '@/components/theme/ThemeProvider';
import { allPermissionIds } from '@/auth/permissions';

const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
  const url = String(input);

  if (url.includes('/v1/session')) {
    return {
      ok: true,
      json: async () => ({ authenticated: true, subject: 'pmo-user', tenant_id: 'tenant-a', roles: ['admin'] }),
    } as Response;
  }

  if (url.includes('/v1/config')) {
    return {
      ok: true,
      json: async () => ({ feature_flags: { agent_async_notifications: true, duplicate_resolution: true } }),
    } as Response;
  }

  if (url.includes('/v1/api/roles')) {
    return { ok: false, status: 500, json: async () => ({}) } as Response;
  }

  if (url.includes('/v1/workflows/approvals')) {
    return { ok: true, json: async () => [] } as Response;
  }

  return { ok: true, json: async () => ({}) } as Response;
});

function renderAt(path: string) {
  return render(
    <I18nProvider>
      <ThemeProvider>
        <MemoryRouter initialEntries={[path]}>
          <App />
        </MemoryRouter>
      </ThemeProvider>
    </I18nProvider>
  );
}

describe('Critical user journeys (route e2e)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    useAppStore.setState({
      session: { authenticated: true, loading: false, user: { id: 'u1', name: 'PMO', email: 'pmo@example.com', tenantId: 'tenant-a', roles: ['admin'], permissions: ['admin:access'] } },
      tenantContext: { tenantId: 'tenant-a', tenantName: 'Tenant A' },
      featureFlags: { agent_async_notifications: true, duplicate_resolution: true },
    });
  });

  it('supports login route', async () => {
    useAppStore.setState({ session: { authenticated: false, loading: false, user: null } });
    renderAt('/login');
    expect(await screen.findByRole('heading', { name: /sign in/i })).toBeInTheDocument();
  });

  it('loads dashboard/home route', async () => {
    renderAt('/');
    expect(await screen.findByRole('heading', { name: /welcome to the ppm platform/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(useAppStore.getState().session.user?.permissions).toEqual(allPermissionIds());
    });
  });

  it('loads approvals route', async () => {
    renderAt('/approvals');
    expect(await screen.findByRole('heading', { name: /My Approvals/i })).toBeInTheDocument();
  });

  it('loads prompt manager route', async () => {
    renderAt('/config/prompts');
    expect(await screen.findByText(/Prompt Manager/i)).toBeInTheDocument();
  });

  it('loads connector status route', async () => {
    renderAt('/config/connectors');
    expect(await screen.findByRole('heading', { name: /Configuration Center/i })).toBeInTheDocument();
  });
});
