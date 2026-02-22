import { useEffect } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { hasPermission, resolvePermissions, type Role } from '@/auth/permissions';
import { useAppStore } from '@/store';
import { ForbiddenPage } from '@/pages/ForbiddenPage';

function isDemoModeEnabled(): boolean {
  const env = import.meta.env as Record<string, unknown>;
  const value = env.DEMO_MODE ?? env.VITE_DEMO_MODE;
  return ['1', 'true', 'yes', 'on'].includes(String(value ?? '').toLowerCase());
}

export function RequireAuth() {
  const { session, setSession, setTenantContext } = useAppStore();

  useEffect(() => {
    if (!session.loading) {
      return;
    }

    let active = true;

    const bootstrapSession = async () => {
      try {
        const response = await fetch('/v1/session');
        const data = await response.json();

        if (!active) {
          return;
        }

        if (!data.authenticated) {
          setSession({ authenticated: false, loading: false, user: null });
          setTenantContext({ tenantId: null, tenantName: null });
          return;
        }

        const roles = data.roles ?? [];
        const user = {
          id: data.subject ?? 'user',
          name: data.subject ?? 'User',
          email: '',
          tenantId: data.tenant_id ?? 'default',
          roles,
          permissions: [] as string[],
        };

        // Fetch role catalog before setting loading=false so that the
        // effect cleanup (triggered by the loading→false state change)
        // does not cancel the in-flight role resolution.
        let permissions: string[] = [];
        try {
          const roleResponse = await fetch('/v1/api/roles');
          if (roleResponse.ok) {
            const roleCatalog = (await roleResponse.json()) as Role[];
            if (active) {
              permissions = resolvePermissions(roles, roleCatalog);
            }
          }
        } catch {
          // Role resolution failed – permissions stay empty (deny-by-default).
        }

        if (!active) {
          return;
        }

        setSession({ authenticated: true, loading: false, user: { ...user, permissions } });
        setTenantContext({
          tenantId: data.tenant_id ?? 'default',
          tenantName: data.tenant_id ?? 'Default Tenant',
        });
      } catch {
        if (!active) {
          return;
        }
        setSession({ authenticated: false, loading: false, user: null });
        setTenantContext({ tenantId: null, tenantName: null });
      }
    };

    bootstrapSession();

    return () => {
      active = false;
    };
  }, [session.loading, setSession, setTenantContext]);

  if (session.loading) {
    return <div aria-live="polite">Loading session…</div>;
  }

  if (!session.authenticated) {
    if (isDemoModeEnabled()) {
      if (typeof window !== 'undefined' && window.location.pathname !== '/') {
        window.location.assign('/');
      }
      return <div aria-live="polite">Bootstrapping demo session…</div>;
    }
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export function RequireTenantContext() {
  const { tenantContext } = useAppStore();

  if (!tenantContext.tenantId) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export function RequireAdminRole() {
  const { session } = useAppStore();
  const isAdmin = session.user?.roles?.includes('admin') || session.user?.permissions?.includes('admin:access');

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}

interface RequirePermissionProps {
  permission: string;
}

export function RequirePermission({ permission }: RequirePermissionProps) {
  const { session } = useAppStore();
  const allowed = hasPermission(session.user?.permissions, permission);

  if (!allowed) {
    return <ForbiddenPage />;
  }

  return <Outlet />;
}
