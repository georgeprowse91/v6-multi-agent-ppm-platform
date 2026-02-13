import React from 'react';
import { Text } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';

import { AppProvider, useAppContext } from '../context/AppContext';
import {
  getSession,
  getAuthTokens,
  setAuthTokens,
  submitProjectStatus,
  fetchApprovals,
  submitApprovalAction,
} from '../api/client';
import { restoreSessionTokens, persistSessionTokens } from '../services/secureSession';
import {
  clearStatusQueue,
  enqueueStatusUpdate,
  loadStatusQueue,
  replayStatusQueue,
} from '../services/statusQueue';
import { ApprovalsScreen } from '../screens/ApprovalsScreen';

jest.mock('../api/client', () => {
  const actual = jest.requireActual('../api/client');
  return {
    ...actual,
    getSession: jest.fn(),
    setAuthTokens: jest.fn(),
    getAuthTokens: jest.fn(),
    submitProjectStatus: jest.fn(),
    fetchApprovals: jest.fn(),
    submitApprovalAction: jest.fn(),
  };
});

jest.mock('../services/secureSession', () => ({
  restoreSessionTokens: jest.fn(),
  persistSessionTokens: jest.fn(),
  clearSessionTokens: jest.fn(),
}));

jest.mock('expo-secure-store', () => {
  const store = new Map<string, string>();
  return {
    getItemAsync: jest.fn((key: string) => Promise.resolve(store.get(key) ?? null)),
    setItemAsync: jest.fn((key: string, value: string) => {
      store.set(key, value);
      return Promise.resolve();
    }),
    deleteItemAsync: jest.fn((key: string) => {
      store.delete(key);
      return Promise.resolve();
    }),
  };
});

const ContextProbe = ({ onReady }: { onReady: (value: ReturnType<typeof useAppContext>) => void }) => {
  const value = useAppContext();
  React.useEffect(() => {
    onReady(value);
  }, [onReady, value]);
  return <Text>probe</Text>;
};

const TenantApprovalsHarness = () => {
  const { setTenantId } = useAppContext();
  React.useEffect(() => {
    setTenantId('tenant-1');
  }, [setTenantId]);
  return <ApprovalsScreen />;
};

describe('mobile integration flows', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    await clearStatusQueue();
  });

  it('bootstraps auth session from secure storage and refreshes session payload', async () => {
    (getAuthTokens as jest.Mock).mockReturnValue(null);
    (restoreSessionTokens as jest.Mock).mockResolvedValue({ accessToken: 'restored' });
    (getSession as jest.Mock).mockResolvedValue({
      authenticated: true,
      tenant_id: 'tenant-1',
      access_token: 'fresh-access',
      refresh_token: 'fresh-refresh',
    });

    let valueRef: ReturnType<typeof useAppContext> | null = null;
    render(
      <AppProvider>
        <ContextProbe onReady={(value) => (valueRef = value)} />
      </AppProvider>
    );

    await waitFor(() => {
      expect(valueRef).not.toBeNull();
    });

    await valueRef?.refreshSession();

    await waitFor(() => {
      expect(valueRef?.session.authenticated).toBe(true);
    });

    expect(setAuthTokens).toHaveBeenCalledWith({ accessToken: 'restored' });
    expect(persistSessionTokens).toHaveBeenCalledWith({
      accessToken: 'fresh-access',
      refreshToken: 'fresh-refresh',
    });
  });

  it('replays queued status updates and keeps failed items for retry', async () => {
    (submitProjectStatus as jest.Mock)
      .mockResolvedValueOnce({ ok: true })
      .mockRejectedValueOnce(new Error('network down'));

    await enqueueStatusUpdate({ project_id: 'p1', status: 'On Track', summary: 'all good' }, 'tenant-1');
    await enqueueStatusUpdate({ project_id: 'p2', status: 'At Risk', summary: 'blocked' }, 'tenant-1');

    const replay = await replayStatusQueue();

    expect(replay.delivered).toBe(1);
    expect(replay.remaining).toBe(1);
    const remaining = await loadStatusQueue();
    expect(remaining).toHaveLength(1);
    expect(remaining[0]?.project_id).toBe('p2');
    expect(remaining[0]?.retries).toBe(1);
  });

  it('submits approval action from approval inbox', async () => {
    (fetchApprovals as jest.Mock).mockResolvedValue([
      { approval_id: 'a-1', title: 'Budget gate', status: 'pending', workflow: 'Gate 2' },
    ]);
    (submitApprovalAction as jest.Mock).mockResolvedValue({ ok: true });

    const screen = render(
      <AppProvider>
        <TenantApprovalsHarness />
      </AppProvider>
    );

    await screen.findByText('Budget gate');
    fireEvent.press(screen.getByText('Approve'));

    await waitFor(() => {
      expect(submitApprovalAction).toHaveBeenCalledWith('a-1', 'approve', 'tenant-1');
    });
  });
});
