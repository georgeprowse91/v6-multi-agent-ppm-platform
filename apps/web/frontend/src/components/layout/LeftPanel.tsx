import { Link, matchPath, useLocation } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useAppStore } from '@/store';
import { MethodologyNav } from '@/components/methodology/MethodologyNav';
import { useMethodologyStore } from '@/store/methodology';
import { useTranslation } from '@/i18n';
import { canManageConfig, canViewAuditLogs, hasPermission } from '@/auth/permissions';
import { Icon } from '@/components/icon/Icon';
import type { IconSemantic } from '@/components/icon/iconMap';
import styles from './LeftPanel.module.css';

interface NavItem {
  id: string;
  label: string;
  icon: IconSemantic;
  path?: string;
  trailingContent?: ReactNode;
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
    id: 'demo-run',
    label: 'Demo Run (25 Agents)',
    path: '/demo-run',
    icon: 'provenance.auditLog',
  },
  {
    id: 'enterprise-uplift',
    label: 'Enterprise Uplift',
    path: '/enterprise-uplift',
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
    matchPath('/app/projects/:projectId/*', pathname) ??
    matchPath('/app/projects/:projectId', pathname) ??
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
  const projectIdFromRoute = getProjectIdFromPathname(location.pathname);
  const sidebarMode = getSidebarMode(location.pathname);
  const projectId =
    sidebarMode === 'project-workspace' ? (projectIdFromRoute ?? selectedProjectId) : null;
  const {
    availableMethodologies,
    projectMethodology,
    hydrateFromWorkspace,
  } = useMethodologyStore();

  const projectIdentityName = useMemo(() => {
    if (!projectId) return null;
    if (currentSelection?.type === 'project' && currentSelection.id === projectId) {
      return currentSelection.name;
    }
    return `Project ${projectId}`;
  }, [currentSelection, projectId]);

  useEffect(() => {
    if (!projectId) return;
    void hydrateFromWorkspace(projectId);
  }, [projectId, hydrateFromWorkspace]);


  const projectWorkspaceNav: NavItem[] = projectId
    ? [
        {
          id: 'knowledge-documents',
          label: 'Documents',
          path: `/knowledge/documents?project=${projectId}`,
          icon: 'artifact.document',
        },
        {
          id: 'knowledge-lessons',
          label: 'Lessons Learned',
          path: `/knowledge/lessons?project=${projectId}`,
          icon: 'ai.explainability',
        },
        {
          id: 'analytics-dashboard',
          label: 'Analytics',
          path: `/analytics/dashboard?project=${projectId}`,
          icon: 'artifact.dashboard',
        },
        {
          id: 'project-performance-dashboard',
          label: 'Performance Dashboard',
          path: `/projects/${projectId}/performance-dashboard`,
          icon: 'artifact.dashboard',
        },
        {
          id: 'project-approvals',
          label: 'My Approvals',
          path: `/approvals?project=${projectId}`,
          icon: 'actions.confirmApply',
          trailingContent: (
            <span
              className={styles.pendingBadgeHook}
              data-testid="project-approvals-pending-badge"
              aria-hidden="true"
            />
          ),
        },
        ...(showProjectConfig
          ? [
              {
                id: 'project-config',
                label: 'Configuration',
                path: `/projects/${projectId}/config`,
                icon: 'actions.settings' as IconSemantic,
              },
            ]
          : []),
      ]
    : [];

  const handleNavKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLElement>) => {
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
    'role-assignments': 'Role Assignments',
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
            path: '/app/admin/roles',
            icon: 'actions.edit' as IconSemantic,
          },
          {
            id: 'role-assignments',
            label: 'Role Assignments',
            path: '/app/admin/roles/assignments',
            icon: 'actions.edit' as IconSemantic,
          },
        ]
      : []),
    ...(showAuditLogs
      ? [
          {
            id: 'audit-logs',
            label: t('nav.auditLogs'),
            path: '/app/admin/audit',
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

  const renderNavItemList = (
    items: NavItem[],
    options?: {
      isActive?: (item: NavItem) => boolean;
    }
  ) => (
    <ul className={styles.navList}>
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
              {!leftPanelCollapsed && <span className={styles.label}>{labelOverrides[item.id] ?? item.label}</span>}
              {!leftPanelCollapsed && item.trailingContent}
            </Link>
          </li>
        );
      })}
    </ul>
  );

  const renderSection = (title: string, content: ReactNode, className?: string) => (
    <div className={`${styles.section} ${className ?? ''}`}>
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
          <button
            type="button"
            className={styles.adminToggle}
            onClick={() => setIsHubAdminExpanded((expanded) => !expanded)}
            aria-expanded={isHubAdminExpanded}
            aria-controls="hub-admin-nav-list"
            title={leftPanelCollapsed ? 'Hub Admin' : undefined}
            aria-label={leftPanelCollapsed ? 'Hub Admin' : undefined}
          >
            <Icon
              semantic="navigation.collapse"
              decorative
              className={styles.adminToggleIcon}
              style={{
                transform: isHubAdminExpanded ? 'rotate(180deg)' : 'rotate(90deg)',
              }}
            />
            {!leftPanelCollapsed && <span className={styles.adminToggleLabel}>Hub Admin</span>}
          </button>
          {isHubAdminExpanded && (
            <div id="hub-admin-nav-list">{renderNavItemList(configItems)}</div>
          )}
        </>
      )}
    </>
  );

  const renderProjectWorkspaceNav = () => (
    <div className={styles.projectWorkspaceLayout}>
      {renderSection(
        'Methodology',
        <div className={styles.projectMethodologySection}>
          {!leftPanelCollapsed && (
            <label className={styles.methodologyPickerLabel}>
              <span>Methodology</span>
              <select
                className={styles.methodologyPicker}
                value={projectMethodology.methodology.id}
                onChange={(event) => {
                  if (!projectId) return;
                  void hydrateFromWorkspace(projectId, event.target.value);
                }}
              >
                {availableMethodologies.map((methodologyId) => (
                  <option key={methodologyId} value={methodologyId}>
                    {methodologyId}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className={styles.methodologyContent}>
            <MethodologyNav collapsed={leftPanelCollapsed} />
          </div>
        </div>
      )}
      {renderSection(
        'Project',
        <div className={styles.projectLinksSection}>
          {renderNavItemList(projectWorkspaceNav, {
            isActive: (item) => {
              if (!item.path) return false;
              const [targetPathname, targetQuery] = item.path.split('?');
              if (targetPathname?.startsWith('/projects/') && targetPathname.endsWith('/config')) {
                return location.pathname.startsWith(targetPathname);
              }
              if (location.pathname !== targetPathname) {
                return false;
              }

              if (!targetQuery) {
                return true;
              }

              const targetParams = new URLSearchParams(targetQuery);
              const locationParams = new URLSearchParams(location.search);
              return Array.from(targetParams.entries()).every(
                ([key, value]) => locationParams.get(key) === value
              );
            },
          })}
        </div>
      )}
    </div>
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


      {sidebarMode === 'project-workspace' && projectIdentityName && (
        <div
          className={styles.projectIdentity}
          title={leftPanelCollapsed ? projectIdentityName : undefined}
          aria-label={leftPanelCollapsed ? projectIdentityName : undefined}
        >
          <span className={styles.projectIdentityName}>{projectIdentityName}</span>
          {!leftPanelCollapsed && <span className={styles.projectIdentityBadge}>Project Workspace</span>}
        </div>
      )}

      <nav
        className={styles.nav}
        id="left-panel-nav"
        aria-label="Primary navigation"
        onKeyDown={handleNavKeyDown}
      >
        {sidebarMode === 'hub' ? renderHubNav() : renderProjectWorkspaceNav()}
      </nav>
    </aside>
  );
}
