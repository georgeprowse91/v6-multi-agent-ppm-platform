import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '@/store';
import { MethodologyNav } from '@/components/methodology';
import styles from './LeftPanel.module.css';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path?: string;
  children?: NavItem[];
}

const configNav: NavItem[] = [
  {
    id: 'agents',
    label: 'Agents',
    path: '/config/agents',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
      </svg>
    ),
  },
  {
    id: 'connectors',
    label: 'Connectors',
    path: '/config/connectors',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path
          fillRule="evenodd"
          d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z"
          clipRule="evenodd"
        />
      </svg>
    ),
  },
  {
    id: 'templates',
    label: 'Templates',
    path: '/config/templates',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
      </svg>
    ),
  },
];

const workflowNav: NavItem[] = [
  {
    id: 'approvals',
    label: 'My Approvals',
    path: '/approvals',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path d="M5 3a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2V7l-4-4H5zm8 1.5L16.5 8H13a1 1 0 01-1-1V4.5zM7 10a1 1 0 011-1h4a1 1 0 110 2H8a1 1 0 01-1-1zm0 4a1 1 0 011-1h6a1 1 0 110 2H8a1 1 0 01-1-1z" />
      </svg>
    ),
  },
  {
    id: 'workflow-monitoring',
    label: 'Workflow Monitor',
    path: '/workflows/monitoring',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path d="M3 3a1 1 0 011-1h3a1 1 0 010 2H5v12h10V4h-2a1 1 0 110-2h3a1 1 0 011 1v14a1 1 0 01-1 1H4a1 1 0 01-1-1V3z" />
        <path d="M7 7a1 1 0 011-1h1a1 1 0 110 2H8a1 1 0 01-1-1zm0 4a1 1 0 011-1h4a1 1 0 110 2H8a1 1 0 01-1-1zm0 4a1 1 0 011-1h6a1 1 0 110 2H8a1 1 0 01-1-1z" />
      </svg>
    ),
  },
];

const knowledgeNav: NavItem[] = [
  {
    id: 'knowledge-documents',
    label: 'Documents',
    path: '/knowledge/documents',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path d="M4 2a2 2 0 00-2 2v12a2 2 0 002 2h9a2 2 0 002-2V7.5a2 2 0 00-.586-1.414l-3.5-3.5A2 2 0 0010.5 2H4zm7 1.5L14.5 7H11a1 1 0 01-1-1V3.5z" />
        <path d="M6 10a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm0 4a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1z" />
      </svg>
    ),
  },
  {
    id: 'knowledge-lessons',
    label: 'Lessons Learned',
    path: '/knowledge/lessons',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path d="M10 2a6 6 0 00-3.536 10.848c.314.22.536.6.536 1.02V15a1 1 0 001 1h4a1 1 0 001-1v-1.132c0-.42.222-.8.536-1.02A6 6 0 0010 2zm-2 13h4v1H8v-1zm4-4.414V11a1 1 0 01-.553.894L10 12.618l-1.447-.724A1 1 0 018 11v-.414A4 4 0 1114 10.586z" />
      </svg>
    ),
  },
];

export function LeftPanel() {
  const location = useLocation();
  const { leftPanelCollapsed, toggleLeftPanel } =
    useAppStore();

  return (
    <aside
      className={`${styles.panel} ${leftPanelCollapsed ? styles.collapsed : ''}`}
    >
      <div className={styles.header}>
        {!leftPanelCollapsed && <h2 className={styles.title}>Navigation</h2>}
        <button
          className={styles.collapseButton}
          onClick={toggleLeftPanel}
          title={leftPanelCollapsed ? 'Expand panel' : 'Collapse panel'}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="currentColor"
            style={{
              transform: leftPanelCollapsed ? 'rotate(180deg)' : 'none',
            }}
          >
            <path
              fillRule="evenodd"
              d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>

      <nav className={styles.nav}>
        {/* Methodology Navigation - Main section */}
        <div className={styles.section}>
          {!leftPanelCollapsed && (
            <h3 className={styles.sectionTitle}>Methodology</h3>
          )}
          <MethodologyNav collapsed={leftPanelCollapsed} />
        </div>

        {/* Configuration Navigation */}
        <div className={styles.section}>
          {!leftPanelCollapsed && (
            <h3 className={styles.sectionTitle}>Configuration</h3>
          )}
          <ul className={styles.navList}>
            {configNav.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.path!}
                  className={`${styles.navItem} ${
                    location.pathname === item.path ? styles.active : ''
                  }`}
                  title={leftPanelCollapsed ? item.label : undefined}
                >
                  <span className={styles.icon}>{item.icon}</span>
                  {!leftPanelCollapsed && (
                    <span className={styles.label}>{item.label}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className={styles.section}>
          {!leftPanelCollapsed && (
            <h3 className={styles.sectionTitle}>Workflow</h3>
          )}
          <ul className={styles.navList}>
            {workflowNav.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.path!}
                  className={`${styles.navItem} ${
                    location.pathname === item.path ? styles.active : ''
                  }`}
                  title={leftPanelCollapsed ? item.label : undefined}
                >
                  <span className={styles.icon}>{item.icon}</span>
                  {!leftPanelCollapsed && (
                    <span className={styles.label}>{item.label}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className={styles.section}>
          {!leftPanelCollapsed && (
            <h3 className={styles.sectionTitle}>Knowledge</h3>
          )}
          <ul className={styles.navList}>
            {knowledgeNav.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.path!}
                  className={`${styles.navItem} ${
                    location.pathname === item.path ? styles.active : ''
                  }`}
                  title={leftPanelCollapsed ? item.label : undefined}
                >
                  <span className={styles.icon}>{item.icon}</span>
                  {!leftPanelCollapsed && (
                    <span className={styles.label}>{item.label}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </nav>
    </aside>
  );
}
