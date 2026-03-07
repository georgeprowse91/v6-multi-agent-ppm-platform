import React, { Suspense, useEffect, useState } from 'react';
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { Skeleton } from '@/components/ui/Skeleton';
import { useAppStore } from '@/store';
import { RequireAdminRole, RequireAuth, RequirePermission, RequireTenantContext } from '@/routing/RouteGuards';
import styles from './App.module.css';

const HomePage = React.lazy(() => import('./pages/HomePage'));
const WorkspacePage = React.lazy(() => import('./pages/WorkspacePage'));
const WorkspaceDirectoryPage = React.lazy(() => import('./pages/WorkspaceDirectoryPage'));
const ConfigPage = React.lazy(() => import('./pages/ConfigPage'));
const ApprovalsPage = React.lazy(() => import('./pages/ApprovalsPage'));
const WorkflowMonitoringPage = React.lazy(() => import('./pages/WorkflowMonitoringPage'));
const WorkflowDesigner = React.lazy(() => import('./pages/WorkflowDesigner'));
const DocumentSearchPage = React.lazy(() => import('./pages/DocumentSearchPage'));
const LessonsLearnedPage = React.lazy(() => import('./pages/LessonsLearnedPage'));
const GlobalSearchPage = React.lazy(() => import('./pages/GlobalSearch'));
const AuditLogPage = React.lazy(() => import('./pages/AuditLogPage'));
const ConnectorMarketplacePage = React.lazy(() => import('./pages/ConnectorMarketplacePage'));
const ConnectorDetailPage = React.lazy(() => import('./pages/ConnectorDetailPage'));
const IntakeFormPage = React.lazy(() => import('./pages/IntakeFormPage'));
const IntakeStatusPage = React.lazy(() => import('./pages/IntakeStatusPage'));
const IntakeApprovalsPage = React.lazy(() => import('./pages/IntakeApprovalsPage'));
const MergeReviewPage = React.lazy(() => import('./pages/MergeReviewPage'));
const AgentRunsPage = React.lazy(() => import('./pages/AgentRunsPage'));
const LoginPage = React.lazy(() => import('./pages/LoginPage'));
const PromptManager = React.lazy(() => import('./pages/PromptManager'));
const AnalyticsDashboard = React.lazy(() => import('./pages/AnalyticsDashboard'));
const PerformanceDashboardPage = React.lazy(() => import('./pages/PerformanceDashboardPage'));
const MethodologyEditor = React.lazy(() => import('./pages/MethodologyEditor'));
const RoleManager = React.lazy(() => import('./pages/RoleManager'));
const ForbiddenPage = React.lazy(() => import('./pages/ForbiddenPage'));
const ProjectConfigPage = React.lazy(() => import('./pages/ProjectConfigPage'));
const NotificationCenterPage = React.lazy(() => import('./pages/NotificationCenterPage'));
const DemoRunPage = React.lazy(() => import('./pages/DemoRunPage'));
const EnterpriseUpliftPage = React.lazy(() => import('./pages/EnterpriseUpliftPage'));
const AgentProfilePage = React.lazy(() => import('./pages/AgentProfilePage'));
const AppLayout = React.lazy(() => import('./components/layout/AppLayout').then((module) => ({ default: module.AppLayout })));

// Enhancement pages
const PredictiveDashboardPage = React.lazy(() => import('./pages/PredictiveDashboardPage'));
const ConnectorHealthDashboardPage = React.lazy(() => import('./pages/ConnectorHealthDashboardPage'));
const ExecutiveBriefingPage = React.lazy(() => import('./pages/ExecutiveBriefingPage'));
const ProjectSetupWizardPage = React.lazy(() => import('./pages/ProjectSetupWizardPage'));
const SecurityPostureDashboardPage = React.lazy(() => import('./pages/SecurityPostureDashboardPage'));
const KnowledgeGraphPage = React.lazy(() => import('./pages/KnowledgeGraphPage'));
const ScenarioAnalysisPage = React.lazy(() => import('./pages/ScenarioAnalysisPage'));
const AgentMarketplacePage = React.lazy(() => import('./pages/AgentMarketplacePage'));
const CapacityPlanningPage = React.lazy(() => import('./pages/CapacityPlanningPage'));
const OrganisationMethodologySettings = React.lazy(() => import('./pages/OrganisationMethodologySettings'));

function isDemoModeEnabled(): boolean {
  const env = import.meta.env as Record<string, unknown>;
  const value = env.DEMO_MODE ?? env.VITE_DEMO_MODE;
  return ['1', 'true', 'yes', 'on'].includes(String(value ?? '').toLowerCase());
}


export function DemoHomeRedirect() {
  const { session } = useAppStore();

  if (isDemoModeEnabled() && session.authenticated) {
    return <Navigate to="/?project_id=demo-predictive" replace />;
  }

  return <HomePage />;
}

function PageSkeleton() {
  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <Skeleton className={styles.headerPrimary} height="2rem" />
        <Skeleton className={styles.headerSecondary} height="2rem" />
      </header>
      <div className={styles.body}>
        <aside className={styles.leftPanel}>
          <Skeleton className={styles.panelTitle} height="1.5rem" />
          <Skeleton className={styles.panelItem} height="2.25rem" />
          <Skeleton className={styles.panelItem} height="2.25rem" />
          <Skeleton className={styles.panelItem} height="2.25rem" />
        </aside>
        <main className={styles.main}>
          <Skeleton className={styles.mainTitle} height="2.25rem" />
          <Skeleton variant="card" className={styles.mainCard} />
          <Skeleton variant="chart" className={styles.mainChart} />
        </main>
      </div>
    </div>
  );
}

function AppRoutes() {
  const { featureFlags } = useAppStore();
  const showMergeReview = featureFlags.duplicate_resolution === true;
  const notificationsEnabled = featureFlags.agent_async_notifications === true;

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<RequireTenantContext />}>
          <Route
            element={(
              <AppLayout>
                <Outlet />
              </AppLayout>
            )}
          >
            <Route path="/" element={<DemoHomeRedirect />} />
            <Route path="/portfolio/:portfolioId" element={<WorkspacePage type="portfolio" />} />
            <Route path="/portfolios/:portfolioId" element={<WorkspacePage type="portfolio" />} />
            <Route path="/portfolios" element={<WorkspaceDirectoryPage type="portfolio" />} />
            <Route path="/program/:programId" element={<WorkspacePage type="program" />} />
            <Route path="/programs/:programId" element={<WorkspacePage type="program" />} />
            <Route path="/programs" element={<WorkspaceDirectoryPage type="program" />} />
            <Route path="/project/:projectId" element={<WorkspacePage type="project" />} />
            <Route path="/projects/:projectId" element={<WorkspacePage type="project" />} />
            <Route path="/projects" element={<WorkspaceDirectoryPage type="project" />} />
            <Route path="/projects/:projectId/config" element={<ProjectConfigPage />} />
            <Route path="/projects/:projectId/config/:tab" element={<ProjectConfigPage />} />
            <Route path="/config/agents" element={<ConfigPage type="agents" />} />
            <Route path="/config/agents/:agent_id" element={<AgentProfilePage />} />
            <Route path="/config/connectors" element={<ConfigPage type="connectors" />} />
            <Route path="/config/connectors/:connector_type_id" element={<ConnectorDetailPage />} />
            <Route path="/app/config/connectors/:connector_type_id" element={<ConnectorDetailPage />} />
            <Route path="/config/workflows" element={<ConfigPage type="workflows" />} />
            <Route path="/config/prompts" element={<PromptManager />} />
            <Route path="/approvals" element={<ApprovalsPage />} />
            <Route path="/workflows/monitoring" element={<WorkflowMonitoringPage />} />
            <Route path="/workflows/designer" element={<WorkflowDesigner />} />
            <Route path="/marketplace/connectors" element={<ConnectorMarketplacePage />} />
            <Route path="/marketplace/agents" element={<AgentMarketplacePage />} />
            <Route path="/intake/new" element={<IntakeFormPage />} />
            <Route path="/intake/status/:requestId" element={<IntakeStatusPage />} />
            <Route path="/intake/approvals" element={<IntakeApprovalsPage />} />
            {showMergeReview && <Route path="/intake/merge-review" element={<MergeReviewPage />} />}
            {notificationsEnabled && <Route path="/notifications" element={<NotificationCenterPage />} />}
            <Route path="/knowledge/documents" element={<DocumentSearchPage />} />
            <Route path="/knowledge/lessons" element={<LessonsLearnedPage />} />
            <Route path="/search" element={<GlobalSearchPage />} />
            <Route element={<RequirePermission permission="audit.view" />}>
              <Route path="/admin/audit" element={<AuditLogPage />} />
              <Route path="/app/admin/audit" element={<AuditLogPage />} />
            </Route>
            <Route element={<RequireAdminRole />}>
              <Route path="/admin/agent-runs" element={<AgentRunsPage />} />
              <Route path="/admin/methodology" element={<MethodologyEditor />} />
              <Route path="/admin/methodology/settings" element={<OrganisationMethodologySettings />} />
            </Route>
            <Route element={<RequirePermission permission="roles.manage" />}>
              <Route path="/admin/roles" element={<RoleManager view="roles" />} />
              <Route path="/app/admin/roles" element={<RoleManager view="roles" />} />
              <Route path="/admin/roles/assignments" element={<RoleManager view="assignments" />} />
              <Route path="/app/admin/roles/assignments" element={<RoleManager view="assignments" />} />
            </Route>
            <Route path="/analytics/dashboard" element={<AnalyticsDashboard />} />
            <Route path="/analytics/predictive" element={<PredictiveDashboardPage />} />
            <Route path="/analytics/briefings" element={<ExecutiveBriefingPage />} />
            <Route path="/analytics/scenarios" element={<ScenarioAnalysisPage />} />
            <Route path="/analytics/capacity" element={<CapacityPlanningPage />} />
            <Route path="/connectors/health" element={<ConnectorHealthDashboardPage />} />
            <Route path="/projects/new" element={<ProjectSetupWizardPage />} />
            <Route path="/knowledge/graph" element={<KnowledgeGraphPage />} />
            <Route path="/admin/security" element={<SecurityPostureDashboardPage />} />
            <Route path="/projects/:projectId/performance-dashboard" element={<PerformanceDashboardPage />} />
            <Route path="/demo-run" element={<DemoRunPage />} />
            <Route path="/enterprise-uplift" element={<EnterpriseUpliftPage />} />
            <Route path="/403" element={<ForbiddenPage />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  );
}

function TransitionedRouter() {
  const location = useLocation();
  const [transitionKey, setTransitionKey] = useState(location.pathname + location.search);

  useEffect(() => {
    const nextKey = location.pathname + location.search;
    const startViewTransition = (
      document as Document & { startViewTransition?: (cb: () => void) => void }
    ).startViewTransition;
    if (typeof startViewTransition === 'function') {
      startViewTransition.call(document, () => {
        setTransitionKey(nextKey);
      });
      return;
    }
    setTransitionKey(nextKey);
  }, [location.pathname, location.search]);

  return (
    <div key={transitionKey} className={styles.routeTransition}>
      <AppRoutes />
    </div>
  );
}

export function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageSkeleton />}>
        <TransitionedRouter />
      </Suspense>
    </ErrorBoundary>
  );
}
