import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { useAppStore } from '@/store';
import { RoleManager } from './RoleManager';

describe('RoleManager', () => {
  afterEach(() => {
    useAppStore.setState({
      session: { authenticated: false, loading: false, user: null },
    });
  });

  it('blocks all role actions when user lacks roles.manage permission', () => {
    useAppStore.setState({
      session: {
        authenticated: true,
        loading: false,
        user: {
          id: 'u1',
          name: 'Read User',
          email: 'readonly@example.com',
          tenantId: 'tenant-1',
          roles: ['TEAM_MEMBER'],
          permissions: ['portfolio.view'],
        },
      },
    });

    render(
      <MemoryRouter>
        <RoleManager view="roles" />
      </MemoryRouter>
    );

    expect(screen.getByText(/do not have permission to manage roles/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /save role/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /update role/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete role/i })).not.toBeInTheDocument();
  });
});
