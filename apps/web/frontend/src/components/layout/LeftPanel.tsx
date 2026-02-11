import { Link, matchPath, useLocation } from 'react-router-dom';
import { useCallback, useState, type ReactNode } from 'react';
import { useAppStore, useMethodologyStore } from '@/store';
import { useTranslation } from '@/i18n';
import { canManageConfig, canViewAuditLogs, hasPermission } from '@/auth/permissions';
import { MethodologyNav } from '@/components/methodology';
import { Icon } from '@/components/icon/Icon';
import type { IconSemantic } from '@/components/icon/iconMap';
import { ProjectMcpSidebar } from '@/components/project/ProjectMcpSidebar';
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

const navigateNav: NavItem[] = [
  {
    id: 'home',
    label: 'Home',
    path: '/',
    icon: 'artifact.dashboard',
  },
  {
    id: 'my-portfolios',
    label: 'My Portfolios',
    path: '/portfolios',
    icon: 'artifact.document',
  },
  {
    id: 'my-programs',
    label: 'My Programs',
    path: '/programs',
    icon: 'provenance.auditLog',
  },
  {
    id: 'my-projects',
    label: 'My Projects',
    path: '/projects',
    icon: 'actions.edit',
  },
];

const workNav: NavItem[] = [
  {
    id: 'intake-new',
    label: 'New Intake',
    path: '/intake/new',
    icon: 'actions.edit' as IconSemantic,
  },
  {
    id: 'approvals',
    label: 'My Approvals',
    path: '/approvals',
    icon: 'actions.confirmApply' as IconSemantic,
  },
  {
    id: 'intake-approvals',
    label: 'Intake Approvals',
    path: '/intake/approvals',
    icon: 'actions.confirmApply' as IconSemantic,
  },
];

const insightsNav: NavItem[] = [
  {
    id: 'analytics-dashboard',
    label: 'Analytics Dashboard',
    path: '/analytics/dashboard',
    icon: 'artifact.dashboard',
  },
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

type SidebarMode = 'hub' | 'project-workspace';

function getProjectIdFromPathname(pathname: string): string | null {
  const projectRouteMatch =
    matchPath('/projects/:projectId/*', pathname) ??
    matchPath('/projects/:projectId', pathname) ??
    matchPath('/project/:projectId', pathname);

  return projectRouteMatch?.params.projectId ?? null;
}

function getSidebarMode(pathname: string): SidebarMode {
  return getProjectIdFromPathname(pathname) ? 'project-workspace' : 'hub';
}

export function LeftPanel() {
  const location = useLocation();
  const {
    leftPanelCollapsed,
    toggleLeftPanel,
    session,
    currentSelection,
    featureFlags,
  } = useAppStore();
  const { t } = useTranslation();
  const showAuditLogs = canViewAuditLogs(session.user?.permissions);
  const showAgentRuns = featureFlags.agent_run_ui === true;
  const showRoleManager = hasPermission(session.user?.permissions, 'roles.manage');
  const showProjectConfig = canManageConfig(session.user?.permissions);
  const showMergeReview = featureFlags.duplicate_resolution === true;
  const showNotifications = featureFlags.agent_async_notifications === true;
  const selectedProjectId = currentSelection?.type === 'project' ? currentSelection.id : null;
  const [isHubAdminExpanded, setIsHubAdminExpanded] = useState(false);
  const projectMethodology = useMethodologyStore((state) => state.projectMethodology);
  const projectIdFromRoute = getProjectIdFromPathname(location.pathname);
  const sidebarMode = getSidebarMode(location.pathname);
  const projectId =
    sidebarMode === 'project-workspace' ? (projectIdFromRoute ?? selectedProjectId) : null;
  const isProjectMethodologyLoaded =
    sidebarMode === 'project-workspace' &&
    !!projectId &&
    projectMethodology.projectId === projectId;
  const projectName = isProjectMethodologyLoaded
    ? projectMethodology.projectName
    : 'Loading project…';
  const methodologyName = isProjectMethodologyLoaded
    ? projectMethodology.methodology.name
    : 'Loading methodology…';

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
    'role-manager': 'Role Management',
    'agent-runs': 'Agent Runs',
    'merge-review': 'Merge Review',
    notifications: 'Notification Center',
  };

  const tourTargets: Record<string, string> = {
    agents: 'nav-agents',
    connectors: 'nav-connectors',
    workflows: 'nav-workflows',
    'workflow-monitoring': 'nav-workflow-monitor',
  };

  const configItems: NavItem[] = [
    ...configNav,
    {
      id: 'workflow-monitoring',
      label: 'Workflow Monitor',
      path: '/workflows/monitoring',
      icon: 'provenance.auditLog' as IconSemantic,
    },
    {
      id: 'methodology-editor',
      label: 'Methodology Editor',
      path: '/admin/methodology',
      icon: 'actions.edit' as IconSemantic,
    },
    ...(showMergeReview
      ? [
          {
            id: 'merge-review',
            label: 'Merge Review',
            path: '/intake/merge-review',
            icon: 'actions.confirmApply' as IconSemantic,
          },
        ]
      : []),
    ...(showNotifications
      ? [
          {
            id: 'notifications',
            label: 'Notification Center',
            path: '/notifications',
            icon: 'communication.notifications' as IconSemantic,
          },
        ]
      : []),
    ...(showRoleManager
      ? [
          {
            id: 'role-manager',
            label: 'Role Management',
            path: '/admin/roles',
            icon: 'actions.edit' as IconSemantic,
          },
        ]
      : []),
    ...(showAuditLogs
      ? [
          {
            id: 'audit-logs',
            label: t('nav.auditLogs'),
            path: '/admin/audit',
            icon: 'provenance.auditLog' as IconSemantic,
          },
        ]
      : []),
    ...(showAgentRuns
      ? [
          {
            id: 'agent-runs',
            label: 'Agent Runs',
            path: '/admin/agent-runs',
            icon: 'provenance.auditLog' as IconSemantic,
          },
        ]
      : []),
  ];

  const projectConfigNav: NavItem[] = projectId
    ? [
        {
          id: 'project-config',
          label: 'Configuration',
          path: `/projects/${projectId}/config`,
          icon: 'actions.settings' as IconSemantic,
        },
      ]
    : [];

  const renderNavItemList = (
    items: NavItem[],
    options?: {
      isActive?: (item: NavItem) => boolean;
    }
  ) => (
    <ul className={styles.navList} onKeyDown={handleNavKeyDown}>
      {items.map((item) => {
        const isActive = options?.isActive ? options.isActive(item) : location.pathname === item.path;

        return (
          <li key={item.id}>
            <Link
              to={item.path!}
              className={`${styles.navItem} ${isActive ? styles.active : ''}`}
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
        );
      })}
    </ul>
  );

  const renderSection = (title: string, content: ReactNode) => (
    <div className={styles.section}>
      {!leftPanelCollapsed && <h3 className={styles.sectionTitle}>{title}</h3>}
      {content}
    </div>
  );

  const renderHubNav = () => (
    <>
      {renderSection('Navigate', renderNavItemList(navigateNav))}
      {renderSection('Work', renderNavItemList(workNav))}
      {renderSection('Insights', renderNavItemList(insightsNav))}
      {renderSection(
        'Admin',
        <>
          {!leftPanelCollapsed && (
            <button
              type="button"
              className={styles.adminToggle}
              onClick={() => setIsHubAdminExpanded((expanded) => !expanded)}
              aria-expanded={isHubAdminExpanded}
              aria-controls="hub-admin-nav-list"
            >
              <Icon
                semantic="navigation.collapse"
                decorative
                className={styles.adminToggleIcon}
                style={{
                  transform: isHubAdminExpanded ? 'rotate(180deg)' : 'rotate(90deg)',
                }}
              />
              <span className={styles.adminToggleLabel}>Hub Admin</span>
            </button>
          )}
          {(leftPanelCollapsed || isHubAdminExpanded) && (
            <div id="hub-admin-nav-list">{renderNavItemList(configItems)}</div>
          )}
        </>
      )}
    </>
  );

  const renderProjectWorkspaceNav = () => (
    <>
      {renderSection('Methodology Map', <MethodologyNav collapsed={leftPanelCollapsed} />)}
      {(showProjectConfig && projectConfigNav.length > 0) || (projectId && !leftPanelCollapsed)
        ? renderSection(
            'Project',
            <>
              {showProjectConfig && projectConfigNav.length > 0
                ? renderNavItemList(projectConfigNav, {
                    isActive: (item) => location.pathname.startsWith(item.path!),
                  })
                : null}
              {projectId && !leftPanelCollapsed && (
                <div className={styles.mcpSidebar}>
                  <ProjectMcpSidebar />
                </div>
              )}
            </>
          )
        : null}
    </>
  );

  return (
    <aside
      className={`${styles.panel} ${leftPanelCollapsed ? styles.collapsed : ''}`}
    >
      <div className={styles.header}>
        {sidebarMode === 'project-workspace' ? (
          <Link
            to="/"
            className={styles.backToHub}
            title={leftPanelCollapsed ? 'Back to Hub' : undefined}
            aria-label={leftPanelCollapsed ? 'Back to Hub' : undefined}
          >
            {!leftPanelCollapsed && <span className={styles.backToHubLabel}>Back to Hub</span>}
            {leftPanelCollapsed && <span aria-hidden="true">←</span>}
          </Link>
        ) : (
          !leftPanelCollapsed && <h2 className={styles.title}>{t('nav.navigation')}</h2>
        )}
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

      {sidebarMode === 'project-workspace' && (
        <div className={styles.projectIdentity} aria-live="polite">
          <span className={styles.projectIdentityName}>{projectName}</span>
          <span className={styles.projectIdentityBadge}>{methodologyName}</span>
        </div>
      )}

      <nav className={styles.nav} id="left-panel-nav" aria-label="Primary navigation">
        {sidebarMode === 'hub' ? renderHubNav() : renderProjectWorkspaceNav()}
      </nav>
    </aside>
  );
}
