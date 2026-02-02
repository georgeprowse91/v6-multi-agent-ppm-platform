import { useEffect } from 'react';
import { Header } from './Header';
import { LeftPanel } from './LeftPanel';
import { MainCanvas } from './MainCanvas';
import { AssistantPanel } from '@/components/assistant';
import { TourProvider } from '@/components/tours';
import { useAppStore } from '@/store';
import { resolvePermissions, type Role } from '@/auth/permissions';
import styles from './AppLayout.module.css';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { setSession } = useAppStore();

  useEffect(() => {
    let mounted = true;
    const loadSession = async () => {
      try {
        const response = await fetch('/session');
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
            permissions: [],
          };
          setSession({
            authenticated: true,
            loading: false,
            user,
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
                permissions,
              },
            });
          } catch {
            if (!mounted) return;
            setSession({ user: { ...user, permissions: [] } });
          }
        } else {
          setSession({ authenticated: false, loading: false, user: null });
        }
      } catch {
        if (!mounted) return;
        setSession({ authenticated: false, loading: false, user: null });
      }
    };
    loadSession();
    return () => {
      mounted = false;
    };
  }, [setSession]);

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
