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

  it('keeps Hub mode free of methodology tree and keeps Hub Admin collapsed by default', () => {
    renderLeftPanel('/');

    expect(screen.queryByRole('navigation', { name: 'Methodology navigation' })).not.toBeInTheDocument();

    const adminToggle = screen.getByRole('button', { name: /Hub Admin/i });
    expect(adminToggle).toHaveAttribute('aria-controls', 'hub-admin-nav-list');
    expect(adminToggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('link', { name: /Agents/i })).not.toBeInTheDocument();

    fireEvent.click(adminToggle);

    expect(adminToggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('link', { name: /Agents/i })).toBeInTheDocument();
  });

  it('applies permission and flag gated admin items and omits MCP standalone section', () => {
    useAppStore.setState({
      session: {
        authenticated: true,
        loading: false,
        user: {
          id: 'u1',
          name: 'User',
          email: 'user@example.com',
          tenantId: 'tenant-1',
          roles: ['PMO_ADMIN'],
          permissions: ['audit.view', 'roles.manage'],
        },
      },
      featureFlags: {
        agent_run_ui: true,
        duplicate_resolution: true,
        agent_async_notifications: true,
      },
    });

    renderLeftPanel('/');
    fireEvent.click(screen.getByRole('button', { name: /Hub Admin/i }));

    expect(screen.getByRole('link', { name: /Role Management/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Audit Logs/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Agent Runs/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Merge Review/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Notification Center/i })).toBeInTheDocument();
    expect(screen.queryByText(/MCP Standalone/i)).not.toBeInTheDocument();
  });

  it('supports arrow/home/end keyboard traversal in Hub mode', () => {
    renderLeftPanel('/');
    fireEvent.click(screen.getByRole('button', { name: /Hub Admin/i }));

    const homeLink = screen.getByRole('link', { name: /Home/i });
    homeLink.focus();

    fireEvent.keyDown(homeLink, { key: 'ArrowDown' });
    expect(screen.getByRole('link', { name: /My Portfolios/i })).toHaveFocus();

    fireEvent.keyDown(screen.getByRole('link', { name: /My Portfolios/i }), { key: 'End' });
    expect(screen.getByRole('link', { name: /Methodology Editor/i })).toHaveFocus();

    fireEvent.keyDown(screen.getByRole('link', { name: /Methodology Editor/i }), { key: 'Home' });
    expect(screen.getByRole('link', { name: /Home/i })).toHaveFocus();
  });

  it('renders project workspace links with project query string and supports keyboard traversal', () => {
    useAppStore.setState({
      currentSelection: {
        type: 'project',
        id: 'project-42',
        name: 'Phoenix Revamp',
      },
    });

    renderLeftPanel('/projects/project-42');

    expect(screen.getByText('Project Workspace')).toBeInTheDocument();

    const documentsLink = screen.getByRole('link', { name: /Documents/i });
    const lessonsLink = screen.getByRole('link', { name: /Lessons Learned/i });
    const analyticsLink = screen.getByRole('link', { name: /Analytics Dashboard/i });
    const approvalsLink = screen.getByRole('link', { name: /My Approvals/i });

    expect(documentsLink).toHaveAttribute('href', '/knowledge/documents?project=project-42');
    expect(lessonsLink).toHaveAttribute('href', '/knowledge/lessons?project=project-42');
    expect(analyticsLink).toHaveAttribute('href', '/analytics/dashboard?project=project-42');
    expect(approvalsLink).toHaveAttribute('href', '/approvals?project=project-42');

    documentsLink.focus();
    fireEvent.keyDown(documentsLink, { key: 'ArrowDown' });
    expect(lessonsLink).toHaveFocus();

    fireEvent.keyDown(lessonsLink, { key: 'End' });
    expect(approvalsLink).toHaveFocus();

    fireEvent.keyDown(approvalsLink, { key: 'Home' });
    expect(documentsLink).toHaveFocus();
  });
});
