import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/i18n';
import { AppLayout } from './AppLayout';

vi.mock('shepherd.js', () => ({
  default: {
    Tour: class {
      addStep = vi.fn();
      start = vi.fn();
      on = vi.fn();
    },
  },
}));

describe('AppLayout', () => {
  afterEach(() => {
    vi.restoreAllMocks();
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
        <MemoryRouter>
          <AppLayout>
            <div>Workspace</div>
          </AppLayout>
        </MemoryRouter>
      </I18nProvider>
    );

    expect(await screen.findByRole('heading', { name: 'Assistant' })).toBeInTheDocument();
  });
});
