import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '@/store';
import styles from './Header.module.css';

interface BreadcrumbItem {
  label: string;
  path?: string;
}

function getBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const parts = pathname.split('/').filter(Boolean);
  const crumbs: BreadcrumbItem[] = [{ label: 'Home', path: '/' }];

  if (parts.length === 0) {
    return crumbs;
  }

  if (parts[0] === 'portfolio' && parts[1]) {
    crumbs.push({ label: 'Portfolio', path: `/portfolio/${parts[1]}` });
  } else if (parts[0] === 'program' && parts[1]) {
    crumbs.push({ label: 'Program', path: `/program/${parts[1]}` });
  } else if (parts[0] === 'project' && parts[1]) {
    crumbs.push({ label: 'Project', path: `/project/${parts[1]}` });
  } else if (parts[0] === 'config') {
    crumbs.push({ label: 'Configuration' });
    if (parts[1] === 'agents') {
      crumbs.push({ label: 'Agents', path: '/config/agents' });
    } else if (parts[1] === 'connectors') {
      crumbs.push({ label: 'Connectors', path: '/config/connectors' });
    } else if (parts[1] === 'workflows') {
      crumbs.push({ label: 'Workflows', path: '/config/workflows' });
    }
  }

  return crumbs;
}

export function Header() {
  const location = useLocation();
  const { session } = useAppStore();
  const breadcrumbs = getBreadcrumbs(location.pathname);

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <Link to="/" className={styles.logo}>
          <svg
            width="28"
            height="28"
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <rect width="32" height="32" rx="4" fill="currentColor" />
            <path
              d="M8 10h4v12H8V10zm6 4h4v8h-4v-8zm6-2h4v10h-4V12z"
              fill="white"
            />
          </svg>
          <span className={styles.logoText}>PPM Platform</span>
        </Link>

        <nav className={styles.breadcrumb} aria-label="Breadcrumb">
          <ol>
            {breadcrumbs.map((crumb, index) => (
              <li key={crumb.path ?? index}>
                {index > 0 && (
                  <span className={styles.separator} aria-hidden="true">
                    /
                  </span>
                )}
                {crumb.path && index < breadcrumbs.length - 1 ? (
                  <Link to={crumb.path}>{crumb.label}</Link>
                ) : (
                  <span aria-current={index === breadcrumbs.length - 1 ? 'page' : undefined}>
                    {crumb.label}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      </div>

      <div className={styles.right}>
        <button className={styles.iconButton} title="Notifications">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
          </svg>
        </button>

        <button className={styles.iconButton} title="Settings">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
              clipRule="evenodd"
            />
          </svg>
        </button>

        <div className={styles.userMenu}>
          <button className={styles.userButton}>
            <div className={styles.avatar}>
              {session.user?.name?.charAt(0).toUpperCase() ?? 'U'}
            </div>
            <span className={styles.userName}>
              {session.user?.name ?? 'User'}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}
