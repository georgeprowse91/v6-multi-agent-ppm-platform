import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '@/App';
import { useAppStore } from '@/store';
import { I18nProvider } from '@/i18n';
import { ThemeProvider } from '@/components/theme/ThemeProvider';

const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
  const url = String(input);

  if (url.includes('/v1/session')) {
    return { ok: true, json: async () => ({ authenticated: true, subject: 'pmo-user', tenant_id: 'tenant-a', roles: ['admin'] }) } as Response;
  }
  if (url.includes('/v1/config')) {
    return { ok: true, json: async () => ({ feature_flags: { agent_async_notifications: true, duplicate_resolution: true } }) } as Response;
  }
  if (url.includes('/api/portfolios') && !url.includes('/api/portfolios/')) {
    return { ok: true, json: async () => ([{ id: 'demo', name: 'Enterprise Transformation', owner: 'PMO', status: 'On track' }]) } as Response;
  }
  if (url.includes('/api/programs') && !url.includes('/api/programs/')) {
    return { ok: true, json: async () => ([{ id: 'demo', name: 'CX Program', owner: 'PMO', status: 'On track' }]) } as Response;
  }
  if (url.includes('/api/projects') && !url.includes('/api/projects/')) {
    return { ok: true, json: async () => ([{ id: 'demo', name: 'Digital Onboarding', owner: 'PMO', status: 'Executing' }]) } as Response;
  }
  if (url.includes('/api/portfolios/demo') || url.includes('/api/programs/demo') || url.includes('/api/projects/demo')) {
    return { ok: true, json: async () => ({ name: 'Demo Workspace', dashboard: { kpis: [{ label: 'Health', value: 'Green' }], relatedItems: [] } }) } as Response;
  }
  if (url.includes('/api/pipeline/')) {
    return { ok: true, json: async () => ({ stages: ['Intake', 'Review'], items: [] }) } as Response;
  }
  if (url.includes('/api/projects/demo/agents')) {
    return { ok: true, json: async () => ([{ agent_id: 'a1', name: 'Risk Agent', description: 'Tracks risk', enabled: true }]) } as Response;
  }
  if (url.includes('/api/projects/demo/connectors')) {
    return { ok: true, json: async () => [] } as Response;
  }

  if (url.includes('/v1/api/intake/')) {
    return {
      ok: true,
      json: async () => ({
        request_id: 'REQ-1001',
        status: 'pending',
        created_at: '2025-01-01',
        updated_at: '2025-01-02',
        sponsor: { name: 'Avery Blake', email: 'avery@example.com', department: 'Operations' },
        business_case: { summary: 'Improve onboarding', justification: 'Reduce cycle time', expected_benefits: 'Faster activation' },
        success_criteria: { metrics: 'Cycle time < 2 days' },
        attachments: { summary: 'Deck and scope', links: [] },
        reviewers: ['pm@example.com'],
      }),
    } as Response;
  }
  if (url.includes('/v1/workflows/approvals')) {
    return { ok: true, json: async () => [] } as Response;
  }

  return { ok: true, json: async () => ({}) } as Response;
});

function renderAt(path: string) {
  cleanup();
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

describe('Critical journeys: login -> launcher -> 4 entry flows', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    useAppStore.setState({
      session: { authenticated: true, loading: false, user: { id: 'u1', name: 'PMO', email: 'pmo@example.com', tenantId: 'tenant-a', roles: ['admin'], permissions: ['admin:access'] } },
      tenantContext: { tenantId: 'tenant-a', tenantName: 'Tenant A' },
      featureFlags: { agent_async_notifications: true, duplicate_resolution: true },
    });
  });

  it('shows login route', async () => {
    useAppStore.setState({ session: { authenticated: false, loading: false, user: null } });
    renderAt('/login');
    expect(await screen.findByRole('heading', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows launcher with all 4 options', async () => {
    renderAt('/');
    expect(await screen.findByRole('button', { name: 'Log new intake' }, { timeout: 5000 })).toBeInTheDocument();
    expect((await screen.findAllByRole('button', { name: 'Open portfolio workspace' })).length).toBeGreaterThan(0);
    expect((await screen.findAllByRole('button', { name: 'Open program workspace' })).length).toBeGreaterThan(0);
    expect((await screen.findAllByRole('button', { name: 'Open project workspace' })).length).toBeGreaterThan(0);
  });

  it('covers new intake flow and downstream pages', async () => {
    renderAt('/intake/new');
    expect(await screen.findByRole('heading', { name: /portfolio intake request/i })).toBeInTheDocument();
    renderAt('/intake/status/REQ-1001');
    expect(await screen.findByRole('heading', { name: /intake request status/i })).toBeInTheDocument();
    renderAt('/intake/approvals');
    expect(await screen.findByRole('heading', { name: /intake approvals/i })).toBeInTheDocument();
  });

  it('covers portfolio and program open flows with downstream pages', async () => {
    renderAt('/portfolios');
    expect(await screen.findByRole('heading', { name: /open portfolio workspace/i })).toBeInTheDocument();
    renderAt('/portfolios/demo');
    expect(await screen.findByRole('heading', { name: /demo workspace/i })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: /methodology map/i })).toBeInTheDocument();

    renderAt('/programs');
    expect(await screen.findByRole('heading', { name: /open program workspace/i })).toBeInTheDocument();
    renderAt('/programs/demo');
    expect(await screen.findByRole('heading', { name: /roadmap and dependency map/i })).toBeInTheDocument();
    renderAt('/workflows/monitoring');
    expect(await screen.findByRole('heading', { name: /workflow monitoring/i })).toBeInTheDocument();
  });

  it('covers project open flow and downstream pages', async () => {
    renderAt('/projects');
    expect(await screen.findByRole('heading', { name: /open project workspace/i })).toBeInTheDocument();
    renderAt('/projects/demo');
    expect(await screen.findByRole('heading', { name: /monitoring & controlling/i })).toBeInTheDocument();
    renderAt('/projects/demo/config');
    expect(await screen.findByRole('tablist', { name: /project configuration tabs/i })).toBeInTheDocument();
  });
});
