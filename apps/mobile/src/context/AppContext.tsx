import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

import { getSession, logout as apiLogout } from '../api/client';

type SessionInfo = {
  authenticated: boolean;
  subject?: string | null;
  tenant_id?: string | null;
  roles?: string[];
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

export const AppProvider = ({ children }: { children: React.ReactNode }) => {
  const [session, setSession] = useState<SessionInfo>({ authenticated: false });
  const [loading, setLoading] = useState<boolean>(true);
  const [tenantId, setTenantIdState] = useState<string | null>(null);

  const refreshSession = useCallback(async () => {
    setLoading(true);
    try {
      const payload = (await getSession()) as SessionInfo;
      setSession(payload);
      if (payload.tenant_id) {
        setTenantIdState(payload.tenant_id);
      }
    } catch (error) {
      setSession({ authenticated: false });
    } finally {
      setLoading(false);
    }
  }, []);

  const setTenantId = useCallback((value: string) => {
    setTenantIdState(value);
  }, []);

  const clearTenantId = useCallback(() => {
    setTenantIdState(null);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setSession({ authenticated: false });
    setTenantIdState(null);
  }, []);

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
