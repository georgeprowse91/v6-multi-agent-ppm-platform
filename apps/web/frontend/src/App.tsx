import { Routes, Route } from 'react-router-dom';
import { AppLayout } from '@/components/layout';
import {
  HomePage,
  WorkspacePage,
  ConfigPage,
  ApprovalsPage,
  WorkflowMonitoringPage,
  DocumentSearchPage,
  LessonsLearnedPage,
  AuditLogPage,
} from '@/pages';

export function App() {
  return (
    <AppLayout>
      <Routes>
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

        {/* Workflow pages */}
        <Route path="/approvals" element={<ApprovalsPage />} />
        <Route path="/workflows/monitoring" element={<WorkflowMonitoringPage />} />

        {/* Knowledge pages */}
        <Route path="/knowledge/documents" element={<DocumentSearchPage />} />
        <Route path="/knowledge/lessons" element={<LessonsLearnedPage />} />

        {/* Admin pages */}
        <Route path="/admin/audit" element={<AuditLogPage />} />
      </Routes>
    </AppLayout>
  );
}
