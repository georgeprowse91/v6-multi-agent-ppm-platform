import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/i18n';
import { AppLayout } from './AppLayout';
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
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ feature_flags: {} }), { status: 200 }));
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
});
