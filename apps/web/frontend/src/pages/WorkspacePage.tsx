import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useAppStore, type EntitySelection } from '@/store';
import styles from './WorkspacePage.module.css';

type EntityType = 'portfolio' | 'program' | 'project';

interface WorkspacePageProps {
  type: EntityType;
}

const typeLabels: Record<EntityType, string> = {
  portfolio: 'Portfolio',
  program: 'Program',
  project: 'Project',
};

const typeDescriptions: Record<EntityType, string> = {
  portfolio:
    'Strategic investment decisions and portfolio-level performance tracking.',
  program:
    'Coordination of related projects to achieve strategic objectives.',
  project: 'Execution of specific deliverables with defined scope and timeline.',
};

const demandPipeline = [
  { stage: 'Intake', count: 14, target: 20, trend: 'steady' },
  { stage: 'Triage', count: 9, target: 15, trend: 'up' },
  { stage: 'Business Case', count: 6, target: 10, trend: 'down' },
  { stage: 'Approval', count: 4, target: 6, trend: 'steady' },
  { stage: 'In Delivery', count: 11, target: 12, trend: 'up' },
];

const charterSnapshots = [
  { id: 'charter-001', name: 'Project Atlas Charter', owner: 'PMO', status: 'Approved', updated: '2 days ago' },
  { id: 'charter-002', name: 'Growth Program Charter', owner: 'Strategy', status: 'In review', updated: 'Yesterday' },
  { id: 'charter-003', name: 'Cloud Migration Charter', owner: 'IT', status: 'Draft', updated: '5 hours ago' },
];

const wbsSnapshot = [
  { name: 'Initiation', children: ['Charter approval', 'Stakeholder alignment'] },
  { name: 'Planning', children: ['WBS', 'Schedule baseline', 'Budget baseline'] },
  { name: 'Execution', children: ['Sprint delivery', 'Vendor onboarding', 'QA checkpoints'] },
  { name: 'Closeout', children: ['Lessons learned', 'Benefits handoff'] },
];

const requirementsSnapshot = [
  { id: 'REQ-118', title: 'Automated demand scoring', priority: 'High', status: 'In progress' },
  { id: 'REQ-121', title: 'Resource capacity heatmap', priority: 'Medium', status: 'Validated' },
  { id: 'REQ-124', title: 'Portfolio health narrative', priority: 'High', status: 'Draft' },
  { id: 'REQ-131', title: 'Risk escalation workflow', priority: 'Medium', status: 'Approved' },
];

const kpiHighlights = [
  { label: 'Portfolio ROI', value: '18.4%', delta: '+1.2%' },
  { label: 'Schedule variance', value: '-2.3%', delta: '+0.6%' },
  { label: 'Budget consumed', value: '64%', delta: '+4%' },
  { label: 'Benefits realized', value: '$4.2M', delta: '+$0.5M' },
];

const riskSummary = [
  { id: 'R-14', title: 'Vendor onboarding delay', severity: 'High', owner: 'Procurement' },
  { id: 'R-18', title: 'Data migration quality', severity: 'Medium', owner: 'IT' },
  { id: 'R-21', title: 'Regulatory sign-off', severity: 'Low', owner: 'Compliance' },
];

const issueSummary = [
  { id: 'I-07', title: 'Sprint capacity shortfall', status: 'Open', owner: 'Delivery' },
  { id: 'I-11', title: 'Integration test failures', status: 'In progress', owner: 'QA' },
  { id: 'I-13', title: 'Scope change request pending', status: 'Escalated', owner: 'PMO' },
];

const healthMetrics = [
  { label: 'Schedule', value: 'On track', status: 'healthy' },
  { label: 'Budget', value: 'Watch', status: 'watch' },
  { label: 'Quality', value: 'At risk', status: 'risk' },
  { label: 'Benefits', value: 'On track', status: 'healthy' },
];

export function WorkspacePage({ type }: WorkspacePageProps) {
  const { portfolioId, programId, projectId } = useParams();
  const { setCurrentSelection, currentActivity, addTab, openTabs } = useAppStore();

  const entityId = portfolioId || programId || projectId || 'unknown';

  useEffect(() => {
    const selection: EntitySelection = {
      type,
      id: entityId,
      name: `${typeLabels[type]} ${entityId}`,
    };
    setCurrentSelection(selection);

    // Add a tab for this workspace if not already open
    const tabId = `${type}-${entityId}`;
    const existingTab = openTabs.find((t) => t.id === tabId);
    if (!existingTab) {
      addTab({
        id: tabId,
        title: `${typeLabels[type]}: ${entityId}`,
        type: 'dashboard',
        entityId,
      });
    }
  }, [type, entityId, setCurrentSelection, addTab, openTabs]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.badge}>{typeLabels[type]}</div>
        <h1 className={styles.title}>{entityId}</h1>
        <p className={styles.description}>{typeDescriptions[type]}</p>
      </header>

      <div className={styles.content}>
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Summary dashboard</h2>
              <p className={styles.sectionSubtitle}>
                Consolidated KPIs, health indicators, and executive highlights for this{' '}
                {typeLabels[type].toLowerCase()}.
              </p>
            </div>
            <button type="button" className={styles.primaryAction}>
              View full dashboard
            </button>
          </div>
          <div className={styles.summaryGrid}>
            {kpiHighlights.map((kpi) => (
              <div key={kpi.label} className={styles.summaryCard}>
                <p className={styles.summaryLabel}>{kpi.label}</p>
                <div className={styles.summaryValue}>{kpi.value}</div>
                <span className={styles.summaryDelta}>{kpi.delta} vs last period</span>
              </div>
            ))}
          </div>
          {currentActivity && (
            <p className={styles.activityNote}>
              Current activity: <strong>{currentActivity.name}</strong>
            </p>
          )}
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Demand pipeline</h2>
          <p className={styles.sectionSubtitle}>
            Visualize pipeline throughput from intake to delivery with targets and trend signals.
          </p>
          <div className={styles.pipeline}>
            {demandPipeline.map((stage) => {
              const percentage = Math.min(
                100,
                Math.round((stage.count / stage.target) * 100)
              );
              return (
                <div key={stage.stage} className={styles.pipelineCard}>
                  <div className={styles.pipelineHeader}>
                    <span className={styles.pipelineStage}>{stage.stage}</span>
                    <span className={styles.pipelineCount}>
                      {stage.count}/{stage.target}
                    </span>
                  </div>
                  <div className={styles.pipelineBar} role="progressbar" aria-valuenow={percentage} aria-valuemin={0} aria-valuemax={100}>
                    <span
                      className={styles.pipelineFill}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className={styles.pipelineTrend}>
                    {stage.trend === 'up' && '▲ Accelerating'}
                    {stage.trend === 'down' && '▼ Slowing'}
                    {stage.trend === 'steady' && '● Steady'}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        <div className={styles.grid}>
          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Health metrics</h3>
            <div className={styles.healthGrid}>
              {healthMetrics.map((metric) => (
                <div key={metric.label} className={styles.healthItem}>
                  <span className={`${styles.healthStatus} ${styles[metric.status]}`}></span>
                  <div>
                    <div className={styles.healthValue}>{metric.value}</div>
                    <div className={styles.healthLabel}>{metric.label}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Charters</h3>
            <ul className={styles.list}>
              {charterSnapshots.map((charter) => (
                <li key={charter.id} className={styles.listItem}>
                  <div>
                    <div className={styles.listTitle}>{charter.name}</div>
                    <div className={styles.listMeta}>
                      Owner: {charter.owner} · Updated {charter.updated}
                    </div>
                  </div>
                  <span className={styles.badge}>{charter.status}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>WBS snapshot</h3>
            <ul className={styles.treeList}>
              {wbsSnapshot.map((item) => (
                <li key={item.name}>
                  <span className={styles.treeTitle}>{item.name}</span>
                  <ul>
                    {item.children.map((child) => (
                      <li key={child} className={styles.treeItem}>
                        {child}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Requirements</h3>
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">ID</th>
                    <th scope="col">Title</th>
                    <th scope="col">Priority</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {requirementsSnapshot.map((req) => (
                    <tr key={req.id}>
                      <td>{req.id}</td>
                      <td>{req.title}</td>
                      <td>{req.priority}</td>
                      <td>{req.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Risks</h3>
            <ul className={styles.list}>
              {riskSummary.map((risk) => (
                <li key={risk.id} className={styles.listItem}>
                  <div>
                    <div className={styles.listTitle}>{risk.title}</div>
                    <div className={styles.listMeta}>Owner: {risk.owner}</div>
                  </div>
                  <span className={`${styles.badge} ${styles[`badge${risk.severity}`]}`}>
                    {risk.severity}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Issues</h3>
            <ul className={styles.list}>
              {issueSummary.map((issue) => (
                <li key={issue.id} className={styles.listItem}>
                  <div>
                    <div className={styles.listTitle}>{issue.title}</div>
                    <div className={styles.listMeta}>Owner: {issue.owner}</div>
                  </div>
                  <span className={styles.badge}>{issue.status}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Stakeholder notification settings</h2>
              <p className={styles.sectionSubtitle}>
                Configure notification cadence and channels for sponsors, delivery leads, and
                governance stakeholders.
              </p>
            </div>
            <button type="button" className={styles.secondaryAction}>
              Save preferences
            </button>
          </div>
          <div className={styles.notificationGrid}>
            <div className={styles.notificationCard}>
              <h3 className={styles.cardSubtitle}>Update cadence</h3>
              <label className={styles.fieldLabel} htmlFor="cadence">
                Summary frequency
              </label>
              <select id="cadence" className={styles.fieldSelect} defaultValue="weekly">
                <option value="daily">Daily digest</option>
                <option value="weekly">Weekly summary</option>
                <option value="monthly">Monthly portfolio review</option>
              </select>
              <label className={styles.fieldLabel} htmlFor="timezone">
                Delivery timezone
              </label>
              <select id="timezone" className={styles.fieldSelect} defaultValue="utc">
                <option value="utc">UTC</option>
                <option value="pst">Pacific (PST)</option>
                <option value="cet">Central Europe (CET)</option>
              </select>
            </div>
            <div className={styles.notificationCard}>
              <h3 className={styles.cardSubtitle}>Notification channels</h3>
              <div className={styles.checkboxGroup}>
                <label>
                  <input type="checkbox" defaultChecked /> Email summaries
                </label>
                <label>
                  <input type="checkbox" defaultChecked /> Slack/Teams alerts
                </label>
                <label>
                  <input type="checkbox" /> Executive PDF pack
                </label>
                <label>
                  <input type="checkbox" defaultChecked /> Risk escalation alerts
                </label>
              </div>
            </div>
            <div className={styles.notificationCard}>
              <h3 className={styles.cardSubtitle}>Stakeholder segments</h3>
              <div className={styles.checkboxGroup}>
                <label>
                  <input type="checkbox" defaultChecked /> Sponsors
                </label>
                <label>
                  <input type="checkbox" defaultChecked /> Delivery leadership
                </label>
                <label>
                  <input type="checkbox" defaultChecked /> Governance board
                </label>
                <label>
                  <input type="checkbox" /> Vendor partners
                </label>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
