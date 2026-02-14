import { useEffect } from 'react';
import { Header } from './Header';
import { LeftPanel } from './LeftPanel';
import { MainCanvas } from './MainCanvas';
import { AssistantPanel } from '@/components/assistant';
import { TourProvider } from '@/components/tours';
import { useAppStore } from '@/store';
import { allPermissionIds, resolvePermissions, type Role } from '@/auth/permissions';
import { useRealtimeConsole } from '@/hooks/useRealtimeConsole';
import styles from './AppLayout.module.css';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { setSession, setFeatureFlags, setTenantContext } = useAppStore();
  useRealtimeConsole();

  useEffect(() => {
    let mounted = true;
    const loadSession = async () => {
      try {
        const response = await fetch('/v1/session');
        const data = await response.json();
        if (!mounted) return;
        if (data.authenticated) {
          const roles = data.roles ?? [];
          const user = {
            id: data.subject ?? 'user',
            name: data.subject ?? 'User',
            email: '',
            tenantId: data.tenant_id ?? 'default',
            roles,
            permissions: allPermissionIds(),
          };
          setSession({
            authenticated: true,
            loading: false,
            user,
          });
          setTenantContext({
            tenantId: data.tenant_id ?? 'default',
            tenantName: data.tenant_id ?? 'Default Tenant',
          });
          try {
            const roleResponse = await fetch('/v1/api/roles');
            if (!roleResponse.ok) {
              throw new Error('Unable to load roles');
            }
            const roleCatalog = (await roleResponse.json()) as Role[];
            if (!mounted) return;
            const permissions = resolvePermissions(roles, roleCatalog);
            setSession({
              user: {
                ...user,
                permissions: permissions.length > 0 ? permissions : allPermissionIds(),
              },
            });
          } catch {
            if (!mounted) return;
            setSession({ user: { ...user, permissions: allPermissionIds() } });
          }
        } else {
          setSession({ authenticated: false, loading: false, user: null });
          setTenantContext({ tenantId: null, tenantName: null });
        }
      } catch {
        if (!mounted) return;
        setSession({ authenticated: false, loading: false, user: null });
        setTenantContext({ tenantId: null, tenantName: null });
      }
    };
    loadSession();
    return () => {
      mounted = false;
    };
  }, [setSession, setTenantContext]);

  useEffect(() => {
    let mounted = true;
    const loadConfig = async () => {
      try {
        const response = await fetch('/v1/config');
        if (!response.ok) {
          throw new Error('Unable to load config');
        }
        const data = await response.json();
        if (!mounted) return;
        setFeatureFlags(data.feature_flags ?? {});
      } catch {
        if (!mounted) return;
        setFeatureFlags({});
      }
    };
    loadConfig();
    return () => {
      mounted = false;
    };
  }, [setFeatureFlags]);

  return (
    <TourProvider>
      <div className={styles.layout}>
        <Header />
        <div className={styles.body}>
          <LeftPanel />
          <MainCanvas>{children}</MainCanvas>
          <AssistantPanel />
        </div>
      </div>
    </TourProvider>
  );
}
