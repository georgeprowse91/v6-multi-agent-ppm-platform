import { Navigate, Route, Routes, Outlet } from 'react-router-dom';
import { AppLayout } from '@/components/layout';
import { useAppStore } from '@/store';
import {
  HomePage,
  WorkspacePage,
  ConfigPage,
  ApprovalsPage,
  WorkflowMonitoringPage,
  WorkflowDesigner,
  DocumentSearchPage,
  LessonsLearnedPage,
  GlobalSearchPage,
  AuditLogPage,
  ConnectorMarketplacePage,
  IntakeFormPage,
  IntakeStatusPage,
  IntakeApprovalsPage,
  MergeReviewPage,
  AgentRunsPage,
  LoginPage,
  PromptManager,
  AnalyticsDashboard,
  MethodologyEditor,
  RoleManager,
  ProjectConfigPage,
  NotificationCenterPage,
} from '@/pages';

interface EntityCollectionRedirectProps {
  type: 'portfolio' | 'program' | 'project';
}

function EntityCollectionRedirect({ type }: EntityCollectionRedirectProps) {
  const { currentSelection } = useAppStore();
  const fallbackPath = `/${type}/demo`;

  if (currentSelection?.type === type && currentSelection.id) {
    return <Navigate replace to={`/${type}/${currentSelection.id}`} />;
  }

  return <Navigate replace to={fallbackPath} />;
}

export function App() {
  const { featureFlags } = useAppStore();
  const showMergeReview = featureFlags.duplicate_resolution === true;
  const notificationsEnabled = featureFlags.agent_async_notifications === true;

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={(
          <AppLayout>
            <Outlet />
          </AppLayout>
        )}
      >
        {/* Home */}
        <Route path="/" element={<HomePage />} />

        {/* Entity workspaces */}
        <Route
          path="/portfolio/:portfolioId"
          element={<WorkspacePage type="portfolio" />}
        />
        <Route
          path="/portfolios/:portfolioId"
          element={<WorkspacePage type="portfolio" />}
        />
        <Route path="/portfolios" element={<EntityCollectionRedirect type="portfolio" />} />
        <Route
          path="/program/:programId"
          element={<WorkspacePage type="program" />}
        />
        <Route
          path="/programs/:programId"
          element={<WorkspacePage type="program" />}
        />
        <Route path="/programs" element={<EntityCollectionRedirect type="program" />} />
        <Route
          path="/project/:projectId"
          element={<WorkspacePage type="project" />}
        />
        <Route
          path="/projects/:projectId"
          element={<WorkspacePage type="project" />}
        />
        <Route path="/projects" element={<EntityCollectionRedirect type="project" />} />
        <Route
          path="/projects/:projectId/config"
          element={<ProjectConfigPage />}
        />
        <Route
          path="/projects/:projectId/config/:tab"
          element={<ProjectConfigPage />}
        />

        {/* Configuration pages */}
        <Route
          path="/config/agents"
          element={<ConfigPage type="agents" />}
        />
        <Route
          path="/config/connectors"
          element={<ConfigPage type="connectors" />}
        />
        <Route
          path="/config/workflows"
          element={<ConfigPage type="workflows" />}
        />
        <Route path="/config/prompts" element={<PromptManager />} />

        {/* Workflow pages */}
        <Route path="/approvals" element={<ApprovalsPage />} />
        <Route path="/workflows/monitoring" element={<WorkflowMonitoringPage />} />
        <Route path="/workflows/designer" element={<WorkflowDesigner />} />
        <Route path="/marketplace/connectors" element={<ConnectorMarketplacePage />} />
        <Route path="/intake/new" element={<IntakeFormPage />} />
        <Route path="/intake/status/:requestId" element={<IntakeStatusPage />} />
        <Route path="/intake/approvals" element={<IntakeApprovalsPage />} />
        {showMergeReview && <Route path="/intake/merge-review" element={<MergeReviewPage />} />}
        {notificationsEnabled && (
          <Route path="/notifications" element={<NotificationCenterPage />} />
        )}

        {/* Knowledge pages */}
        <Route path="/knowledge/documents" element={<DocumentSearchPage />} />
        <Route path="/knowledge/lessons" element={<LessonsLearnedPage />} />
        <Route path="/search" element={<GlobalSearchPage />} />

        {/* Admin pages */}
        <Route path="/admin/audit" element={<AuditLogPage />} />
        <Route path="/admin/agent-runs" element={<AgentRunsPage />} />
        <Route path="/admin/methodology" element={<MethodologyEditor />} />
        <Route path="/admin/roles" element={<RoleManager />} />

        {/* Analytics */}
        <Route path="/analytics/dashboard" element={<AnalyticsDashboard />} />
      </Route>
    </Routes>
  );
}
