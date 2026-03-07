import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { hasPermission } from '@/auth/permissions';
import { useAppStore } from '@/store';
import { ScenarioBuilder } from '@/components/analytics/ScenarioBuilder';
import styles from './AnalyticsDashboard.module.css';

export function ScenarioAnalysisPage() {
  const { currentSelection, session } = useAppStore();
  const [searchParams] = useSearchParams();
  const projectFromQuery = searchParams.get('project');
  const portfolioFromQuery = searchParams.get('portfolio');
  const [projectId, setProjectId] = useState(
    projectFromQuery ?? currentSelection?.id ?? 'demo-project'
  );
  const canViewAnalytics = hasPermission(session.user?.permissions, 'analytics.view');

  if (!canViewAnalytics) {
    return (
      <section className={styles.page}>
        <div className={styles.emptyState}>
          You do not have permission to view analytics dashboards.
        </div>
      </section>
    );
  }

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>What-If Scenario Analysis</h1>
          <p className={styles.subtitle}>
            Run what-if scenario analyses with preset templates or custom parameters.
            Compare scenarios side-by-side and assess cascade impacts across linked projects.
          </p>
        </div>
        <div className={styles.controls}>
          <input
            className={styles.input}
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            placeholder="Project ID"
            aria-label="Project ID"
          />
        </div>
      </header>

      <ScenarioBuilder
        projectId={projectId}
        portfolioId={portfolioFromQuery ?? undefined}
      />
    </section>
  );
}

export default ScenarioAnalysisPage;
