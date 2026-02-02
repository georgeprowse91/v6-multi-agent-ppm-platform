import { Link, useLocation } from 'react-router-dom';
import { useCallback } from 'react';
import { useAppStore } from '@/store';
import { useTranslation } from '@/i18n';
import { canViewAuditLogs } from '@/auth/permissions';
import { MethodologyNav } from '@/components/methodology';
import { Icon } from '@/components/icon/Icon';
import type { IconSemantic } from '@/components/icon/iconMap';
import styles from './LeftPanel.module.css';

interface NavItem {
  id: string;
  label: string;
  icon: IconSemantic;
  path?: string;
  children?: NavItem[];
}

const configNav: NavItem[] = [
  {
    id: 'agents',
    label: 'Agents',
    path: '/config/agents',
    icon: 'communication.assistant',
  },
  {
    id: 'connectors',
    label: 'Connectors',
    path: '/config/connectors',
    icon: 'provenance.link',
  },
  {
    id: 'workflows',
    label: 'Workflows',
    path: '/config/workflows',
    icon: 'ai.automation',
  },
  {
    id: 'prompts',
    label: 'Prompt Library',
    path: '/config/prompts',
    icon: 'communication.assistant',
  },
];

const workflowNav: NavItem[] = [
  {
    id: 'approvals',
    label: 'My Approvals',
    path: '/approvals',
    icon: 'actions.confirmApply',
  },
  {
    id: 'intake-new',
    label: 'New Intake',
    path: '/intake/new',
    icon: 'actions.edit',
  },
  {
    id: 'intake-approvals',
    label: 'Intake Approvals',
    path: '/intake/approvals',
    icon: 'actions.confirmApply',
  },
  {
    id: 'workflow-monitoring',
    label: 'Workflow Monitor',
    path: '/workflows/monitoring',
    icon: 'provenance.auditLog',
  },
];

const knowledgeNav: NavItem[] = [
  {
    id: 'knowledge-documents',
    label: 'Documents',
    path: '/knowledge/documents',
    icon: 'artifact.document',
  },
  {
    id: 'knowledge-lessons',
    label: 'Lessons Learned',
    path: '/knowledge/lessons',
    icon: 'ai.explainability',
  },
];

const analyticsNav: NavItem[] = [
  {
    id: 'analytics-dashboard',
    label: 'Analytics Dashboard',
    path: '/analytics/dashboard',
    icon: 'artifact.dashboard',
  },
];

export function LeftPanel() {
  const location = useLocation();
  const { leftPanelCollapsed, toggleLeftPanel, session } = useAppStore();
  const { t } = useTranslation();
  const showAuditLogs = canViewAuditLogs(session.user?.roles);

  const handleNavKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLUListElement>) => {
      const keys = ['ArrowDown', 'ArrowUp', 'Home', 'End'];
      if (!keys.includes(event.key)) return;
      const items = Array.from(
        event.currentTarget.querySelectorAll<HTMLElement>('a[data-nav-item="true"]')
      );
      if (!items.length) return;
      const currentIndex = items.indexOf(document.activeElement as HTMLElement);
      if (currentIndex === -1) return;
      event.preventDefault();
      let nextIndex = currentIndex;
      if (event.key === 'ArrowDown') nextIndex = (currentIndex + 1) % items.length;
      if (event.key === 'ArrowUp') nextIndex = (currentIndex - 1 + items.length) % items.length;
      if (event.key === 'Home') nextIndex = 0;
      if (event.key === 'End') nextIndex = items.length - 1;
      items[nextIndex]?.focus();
    },
    []
  );

  const labelOverrides: Record<string, string> = {
    agents: t('nav.agents'),
    connectors: t('nav.connectors'),
    workflows: t('nav.workflowRouting'),
    approvals: t('nav.approvals'),
    'workflow-monitoring': t('nav.workflowMonitor'),
    'knowledge-documents': t('nav.documents'),
    'knowledge-lessons': t('nav.lessons'),
    prompts: t('nav.promptLibrary'),
    'analytics-dashboard': t('nav.analyticsDashboard'),
  };

  const tourTargets: Record<string, string> = {
    agents: 'nav-agents',
    connectors: 'nav-connectors',
    workflows: 'nav-workflows',
    'workflow-monitoring': 'nav-workflow-monitor',
  };

  const configItems = [
    ...configNav,
    ...(showAuditLogs
      ? [
          {
            id: 'audit-logs',
            label: t('nav.auditLogs'),
            path: '/admin/audit',
            icon: 'provenance.auditLog',
          },
        ]
      : []),
  ];

  return (
    <aside
      className={`${styles.panel} ${leftPanelCollapsed ? styles.collapsed : ''}`}
    >
      <div className={styles.header}>
        {!leftPanelCollapsed && <h2 className={styles.title}>{t('nav.navigation')}</h2>}
        <button
          type="button"
          className={styles.collapseButton}
          onClick={toggleLeftPanel}
          title={leftPanelCollapsed ? 'Expand panel' : 'Collapse panel'}
          aria-label={leftPanelCollapsed ? 'Expand navigation panel' : 'Collapse navigation panel'}
          aria-expanded={!leftPanelCollapsed}
          aria-controls="left-panel-nav"
        >
          <Icon
            semantic="navigation.collapse"
            label={leftPanelCollapsed ? 'Expand navigation panel' : 'Collapse navigation panel'}
            style={{
              transform: leftPanelCollapsed ? 'rotate(180deg)' : 'none',
            }}
          />
        </button>
      </div>

      <nav className={styles.nav} id="left-panel-nav" aria-label="Primary navigation">
        {/* Methodology Navigation - Main section */}
        <div className={styles.section}>
          {!leftPanelCollapsed && (
            <h3 className={styles.sectionTitle}>{t('nav.methodology')}</h3>
          )}
          <MethodologyNav collapsed={leftPanelCollapsed} />
        </div>

        {/* Configuration Navigation */}
        <div className={styles.section}>
          {!leftPanelCollapsed && (
            <h3 className={styles.sectionTitle}>{t('nav.configuration')}</h3>
          )}
          <ul className={styles.navList} onKeyDown={handleNavKeyDown}>
            {configItems.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.path!}
                  className={`${styles.navItem} ${
                    location.pathname === item.path ? styles.active : ''
                  }`}
                  title={leftPanelCollapsed ? (labelOverrides[item.id] ?? item.label) : undefined}
                  aria-label={leftPanelCollapsed ? (labelOverrides[item.id] ?? item.label) : undefined}
                  data-nav-item="true"
                  data-tour={tourTargets[item.id] ?? undefined}
                >
                  <Icon semantic={item.icon} decorative className={styles.icon} />
                  {!leftPanelCollapsed && (
                    <span className={styles.label}>{labelOverrides[item.id] ?? item.label}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className={styles.section}>
          {!leftPanelCollapsed && (
            <h3 className={styles.sectionTitle}>{t('nav.workflow')}</h3>
          )}
          <ul className={styles.navList} onKeyDown={handleNavKeyDown}>
            {workflowNav.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.path!}
                  className={`${styles.navItem} ${
                    location.pathname === item.path ? styles.active : ''
                  }`}
                  title={leftPanelCollapsed ? (labelOverrides[item.id] ?? item.label) : undefined}
                  aria-label={leftPanelCollapsed ? (labelOverrides[item.id] ?? item.label) : undefined}
                  data-nav-item="true"
                  data-tour={tourTargets[item.id] ?? undefined}
                >
                  <Icon semantic={item.icon} decorative className={styles.icon} />
                  {!leftPanelCollapsed && (
                    <span className={styles.label}>{labelOverrides[item.id] ?? item.label}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className={styles.section}>
          {!leftPanelCollapsed && (
            <h3 className={styles.sectionTitle}>{t('nav.knowledge')}</h3>
          )}
          <ul className={styles.navList} onKeyDown={handleNavKeyDown}>
            {knowledgeNav.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.path!}
                  className={`${styles.navItem} ${
                    location.pathname === item.path ? styles.active : ''
                  }`}
                  title={leftPanelCollapsed ? (labelOverrides[item.id] ?? item.label) : undefined}
                  aria-label={leftPanelCollapsed ? (labelOverrides[item.id] ?? item.label) : undefined}
                  data-nav-item="true"
                  data-tour={tourTargets[item.id] ?? undefined}
                >
                  <Icon semantic={item.icon} decorative className={styles.icon} />
                  {!leftPanelCollapsed && (
                    <span className={styles.label}>{labelOverrides[item.id] ?? item.label}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className={styles.section}>
          {!leftPanelCollapsed && <h3 className={styles.sectionTitle}>Analytics</h3>}
          <ul className={styles.navList} onKeyDown={handleNavKeyDown}>
            {analyticsNav.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.path!}
                  className={`${styles.navItem} ${
                    location.pathname === item.path ? styles.active : ''
                  }`}
                  title={leftPanelCollapsed ? (labelOverrides[item.id] ?? item.label) : undefined}
                  aria-label={leftPanelCollapsed ? (labelOverrides[item.id] ?? item.label) : undefined}
                  data-nav-item="true"
                >
                  <Icon semantic={item.icon} decorative className={styles.icon} />
                  {!leftPanelCollapsed && (
                    <span className={styles.label}>{labelOverrides[item.id] ?? item.label}</span>
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
