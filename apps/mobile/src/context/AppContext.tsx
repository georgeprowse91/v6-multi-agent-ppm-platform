import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

import {
  getSession,
  getAuthTokens,
  logout as apiLogout,
  setAuthTokens,
  type AuthTokens,
} from '../api/client';
import {
  clearSessionTokens,
  persistSessionTokens,
  restoreSessionTokens,
} from '../services/secureSession';
import { reportCrash } from '../services/telemetry';

type SessionInfo = {
  authenticated: boolean;
  subject?: string | null;
  tenant_id?: string | null;
  roles?: string[];
  access_token?: string | null;
  refresh_token?: string | null;
};

type AppContextValue = {
  session: SessionInfo;
  loading: boolean;
  tenantId: string | null;
  projectId: string;
  refreshSession: () => Promise<void>;
  setTenantId: (tenantId: string) => void;
  clearTenantId: () => void;
  logout: () => Promise<void>;
};

const AppContext = createContext<AppContextValue | undefined>(undefined);

const DEFAULT_PROJECT_ID = 'default-project';

const toTokens = (session: SessionInfo): AuthTokens | null => {
  if (!session.access_token) {
    return null;
  }
  return {
    accessToken: session.access_token,
    ...(session.refresh_token ? { refreshToken: session.refresh_token } : {}),
  };
};

export const AppProvider = ({ children }: { children: React.ReactNode }) => {
  const [session, setSession] = useState<SessionInfo>({ authenticated: false });
  const [loading, setLoading] = useState<boolean>(true);
  const [tenantId, setTenantIdState] = useState<string | null>(null);

  const clearAuthState = useCallback(async () => {
    setAuthTokens(null);
    await clearSessionTokens();
    setSession({ authenticated: false });
    setTenantIdState(null);
  }, []);

  const refreshSession = useCallback(async () => {
    setLoading(true);
    try {
      if (!getAuthTokens()) {
        const restoredTokens = await restoreSessionTokens();
        if (restoredTokens) {
          setAuthTokens(restoredTokens);
        }
      }

      const payload = (await getSession()) as SessionInfo;
      setSession(payload);

      const nextTokens = toTokens(payload);
      if (nextTokens) {
        setAuthTokens(nextTokens);
        await persistSessionTokens(nextTokens);
      }

      if (payload.tenant_id) {
        setTenantIdState(payload.tenant_id);
      }
    } catch (error) {
      reportCrash(error instanceof Error ? error : new Error('Unknown session restore failure'), {
        phase: 'session_restore',
        sessionAuthenticated: Boolean(getAuthTokens()),
        tenantId: null,
      });
      await clearAuthState();
    } finally {
      setLoading(false);
    }
  }, [clearAuthState]);

  const setTenantId = useCallback((value: string) => {
    setTenantIdState(value);
  }, []);

  const clearTenantId = useCallback(() => {
    setTenantIdState(null);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      await clearAuthState();
    }
  }, [clearAuthState]);

  const value = useMemo(
    () => ({
      session,
      loading,
      tenantId,
      projectId: DEFAULT_PROJECT_ID,
      refreshSession,
      setTenantId,
      clearTenantId,
      logout,
    }),
    [session, loading, tenantId, refreshSession, setTenantId, clearTenantId, logout]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return context;
};
