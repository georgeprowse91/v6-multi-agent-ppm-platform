import { Routes, Route, Outlet } from 'react-router-dom';
import { AppLayout } from '@/components/layout';
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
  LoginPage,
  PromptManager,
  AnalyticsDashboard,
  MethodologyEditor,
  RoleManager,
} from '@/pages';

export function App() {
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
          path="/program/:programId"
          element={<WorkspacePage type="program" />}
        />
        <Route
          path="/project/:projectId"
          element={<WorkspacePage type="project" />}
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

        {/* Knowledge pages */}
        <Route path="/knowledge/documents" element={<DocumentSearchPage />} />
        <Route path="/knowledge/lessons" element={<LessonsLearnedPage />} />
        <Route path="/search" element={<GlobalSearchPage />} />

        {/* Admin pages */}
        <Route path="/admin/audit" element={<AuditLogPage />} />
        <Route path="/admin/methodology" element={<MethodologyEditor />} />
        <Route path="/admin/roles" element={<RoleManager />} />

        {/* Analytics */}
        <Route path="/analytics/dashboard" element={<AnalyticsDashboard />} />
      </Route>
    </Routes>
  );
}
