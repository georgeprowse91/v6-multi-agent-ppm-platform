import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/i18n';
import { useAppStore } from '@/store';
import { LeftPanel } from './LeftPanel';


vi.mock('@/components/icon/Icon', () => ({
  Icon: ({ label }: { label?: string }) => <span>{label ?? 'icon'}</span>,
}));
function renderLeftPanel(initialEntry = '/') {
  return render(
    <I18nProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <LeftPanel />
      </MemoryRouter>
    </I18nProvider>
  );
}

describe('LeftPanel', () => {
  afterEach(() => {
    useAppStore.setState({
      leftPanelCollapsed: false,
      rightPanelCollapsed: false,
      currentSelection: null,
      featureFlags: {},
      session: {
        authenticated: false,
        loading: false,
        user: null,
      },
    });
  });

  it('sets semantic attributes and toggles the Hub Admin accordion', () => {
    renderLeftPanel('/');

    const adminToggle = screen.getByRole('button', { name: /Hub Admin/ });
    expect(adminToggle).toHaveAttribute('aria-controls', 'hub-admin-nav-list');
    expect(adminToggle).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(adminToggle);

    expect(adminToggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('link', { name: /Agents/ })).toBeInTheDocument();
  });

  it('keeps keyboard traversal across visible Hub nav items including expanded Admin list', () => {
    renderLeftPanel('/');

    fireEvent.click(screen.getByRole('button', { name: /Hub Admin/ }));

    const firstNavLink = screen.getByRole('link', { name: /Home/ });
    firstNavLink.focus();
    fireEvent.keyDown(firstNavLink, { key: 'End' });

    expect(screen.getByRole('link', { name: /Methodology Editor/ })).toHaveFocus();
  });

  it('shows project identity and preserves accessible icon-only mode in project workspace', () => {
    useAppStore.setState({
      leftPanelCollapsed: true,
      currentSelection: {
        type: 'project',
        id: 'project-42',
        name: 'Phoenix Revamp',
      },
    });

    renderLeftPanel('/projects/project-42');

    expect(screen.getByText('Phoenix Revamp')).toBeInTheDocument();
    expect(screen.getByLabelText('Phoenix Revamp')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back to Hub/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Documents/ })).toBeInTheDocument();

    const documentsLink = screen.getByRole('link', { name: /Documents/ });
    documentsLink.focus();
    fireEvent.keyDown(documentsLink, { key: 'ArrowDown' });

    expect(screen.getByRole('link', { name: /Lessons Learned/ })).toHaveFocus();
  });
});
