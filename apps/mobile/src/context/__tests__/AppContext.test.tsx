import React, { useEffect } from 'react';
import { Text } from 'react-native';
import { render, waitFor } from '@testing-library/react-native';

import { AppProvider, useAppContext } from '../AppContext';
import {
  getSession,
  setAuthTokens,
  getAuthTokens,
  logout as apiLogout,
} from '../../api/client';
import { restoreSessionTokens, persistSessionTokens } from '../../services/secureSession';

jest.mock('../../api/client', () => {
  const actual = jest.requireActual('../../api/client');
  return {
    ...actual,
    getSession: jest.fn(),
    logout: jest.fn(),
    setAuthTokens: jest.fn(),
    getAuthTokens: jest.fn(),
  };
});

jest.mock('../../services/secureSession', () => ({
  restoreSessionTokens: jest.fn(),
  persistSessionTokens: jest.fn(),
  clearSessionTokens: jest.fn(),
}));

const ContextProbe = ({
  onReady,
  bootstrap = false,
}: {
  onReady: (value: ReturnType<typeof useAppContext>) => void;
  bootstrap?: boolean;
}) => {
  const value = useAppContext();
  useEffect(() => {
    onReady(value);
  }, [onReady, value]);

  useEffect(() => {
    if (bootstrap) {
      void value.refreshSession();
    }
  }, [bootstrap, value]);

  return <Text>probe</Text>;
};

describe('AppProvider session restoration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (getAuthTokens as jest.Mock).mockReturnValue(null);
    (restoreSessionTokens as jest.Mock).mockResolvedValue({ accessToken: 'restored-token' });
    (getSession as jest.Mock).mockResolvedValue({
      authenticated: true,
      tenant_id: 'tenant-a',
      access_token: 'new-access',
      refresh_token: 'new-refresh',
    });
  });

  it('restores tokens and refreshes session on bootstrap', async () => {
    let contextRef: ReturnType<typeof useAppContext> | null = null;

    render(
      <AppProvider>
        <ContextProbe bootstrap onReady={(value) => (contextRef = value)} />
      </AppProvider>
    );

    await waitFor(() => {
      expect(contextRef?.loading).toBe(false);
    });

    await waitFor(() => {
      expect(setAuthTokens).toHaveBeenCalledWith({ accessToken: 'restored-token' });
    });

    expect(persistSessionTokens).toHaveBeenCalledWith({
      accessToken: 'new-access',
      refreshToken: 'new-refresh',
    });
    expect(contextRef?.session.authenticated).toBe(true);
    expect(contextRef?.tenantId).toBe('tenant-a');
  });

  it('clears auth state when token is invalidated', async () => {
    let contextRef: ReturnType<typeof useAppContext> | null = null;
    (restoreSessionTokens as jest.Mock).mockResolvedValue({ accessToken: 'stale-token' });
    (getSession as jest.Mock).mockRejectedValue(new Error('Unauthorized'));

    render(
      <AppProvider>
        <ContextProbe bootstrap onReady={(value) => (contextRef = value)} />
      </AppProvider>
    );

    await waitFor(() => {
      expect(contextRef?.loading).toBe(false);
    });

    expect(contextRef?.session.authenticated).toBe(false);

    await waitFor(() => {
      expect(setAuthTokens).toHaveBeenCalledWith(null);
    });

    await contextRef?.logout();
    expect(apiLogout).toHaveBeenCalled();
  });
});
