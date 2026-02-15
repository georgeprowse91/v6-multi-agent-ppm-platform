import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import styles from './PerformanceDashboardPage.module.css';

interface HealthPayload {
  status?: string;
  composite_score?: number;
  spi?: number;
  cpi?: number;
}

interface TrendPoint {
  timestamp?: string;
  composite_score?: number;
}

interface TrendPayload {
  points?: TrendPoint[];
}

interface QualityPayload {
  pass_rate?: number;
  total_rules?: number;
  violations?: Array<{ rule?: string; count?: number }>;
}

interface KpiPayload {
  metrics?: Array<{ name: string; value: number | null; normalized: number }>;
  computed_at?: string;
}

interface NarrativePayload {
  summary?: string;
  highlights?: string[];
  risks?: string[];
  opportunities?: string[];
}

interface DrillItem {
  id: string;
  title: string;
  owner?: string;
  severity?: string;
  status?: string;
}

const API_BASE = '/api/dashboard';

export default function PerformanceDashboardPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [trends, setTrends] = useState<TrendPayload | null>(null);
  const [quality, setQuality] = useState<QualityPayload | null>(null);
  const [kpis, setKpis] = useState<KpiPayload | null>(null);
  const [narrative, setNarrative] = useState<NarrativePayload | null>(null);
  const [risks, setRisks] = useState<DrillItem[]>([]);
  const [issues, setIssues] = useState<DrillItem[]>([]);
  const [approvals, setApprovals] = useState<Array<{ id?: string; title?: string; project?: string }>>([]);
  const [whatIfMessage, setWhatIfMessage] = useState('');
  const [whatIfBusy, setWhatIfBusy] = useState(false);
  const [exportMessage, setExportMessage] = useState('');

  useEffect(() => {
    if (!projectId) return;
    const load = async () => {
      const [healthRes, trendsRes, qualityRes, kpiRes, narrativeRes, risksRes, issuesRes, approvalsRes] = await Promise.all([
        fetch(`${API_BASE}/${projectId}/health`),
        fetch(`${API_BASE}/${projectId}/trends`),
        fetch(`${API_BASE}/${projectId}/quality`),
        fetch(`${API_BASE}/${projectId}/kpis`),
        fetch(`${API_BASE}/${projectId}/narrative`),
        fetch(`${API_BASE}/${projectId}/risks`),
        fetch(`${API_BASE}/${projectId}/issues`),
        fetch('/api/approvals'),
      ]);
      if (healthRes.ok) setHealth((await healthRes.json()) as HealthPayload);
      if (trendsRes.ok) setTrends((await trendsRes.json()) as TrendPayload);
      if (qualityRes.ok) setQuality((await qualityRes.json()) as QualityPayload);
      if (kpiRes.ok) setKpis((await kpiRes.json()) as KpiPayload);
      if (narrativeRes.ok) setNarrative((await narrativeRes.json()) as NarrativePayload);
      if (risksRes.ok) setRisks(((await risksRes.json()) as { items?: DrillItem[] }).items ?? []);
      if (issuesRes.ok) setIssues(((await issuesRes.json()) as { items?: DrillItem[] }).items ?? []);
      if (approvalsRes.ok) {
        const payload = (await approvalsRes.json()) as { approvals?: Array<{ id?: string; title?: string; project?: string }>; items?: Array<{ id?: string; title?: string; project?: string }> };
        setApprovals(payload.approvals ?? payload.items ?? []);
      }
    };
    void load();
  }, [projectId]);

  const filteredApprovals = useMemo(
    () => approvals.filter((item) => !projectId || item.project === projectId).slice(0, 5),
    [approvals, projectId]
  );

  const runWhatIf = async () => {
    if (!projectId) return;
    setWhatIfBusy(true);
    setWhatIfMessage('');
    const response = await fetch(`${API_BASE}/${projectId}/what-if`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario: 'Improve risk and schedule posture',
        adjustments: { risk_score: 0.08, schedule_variance: 0.06 },
      }),
    });
    setWhatIfBusy(false);
    if (!response.ok) {
      setWhatIfMessage('What-if request failed.');
      return;
    }
    const payload = (await response.json()) as { scenario_id?: string; status?: string };
    setWhatIfMessage(`Scenario ${payload.scenario_id ?? 'N/A'} is ${payload.status ?? 'processed'}.`);
  };

  const exportPack = async () => {
    if (!projectId) return;
    setExportMessage('');
    const response = await fetch(`${API_BASE}/${projectId}/export-pack`, { method: 'POST' });
    if (!response.ok) {
      setExportMessage('Export failed.');
      return;
    }
    const payload = (await response.json()) as { download_path: string; file_name: string };
    setExportMessage(`Exported ${payload.file_name} to ${payload.download_path}`);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Performance Dashboard</h1>
        <p>Health, trends, quality, KPI metrics, narrative insights, and actions.</p>
        <div className={styles.actions}>
          <button onClick={runWhatIf} disabled={whatIfBusy}>{whatIfBusy ? 'Running…' : 'Run what-if scenario'}</button>
          <button onClick={exportPack}>Export dashboard pack</button>
          <button onClick={() => navigate(`/projects/${encodeURIComponent(projectId ?? '')}`)}>Back to workspace</button>
        </div>
        {whatIfMessage && <p>{whatIfMessage}</p>}
        {exportMessage && <p>{exportMessage}</p>}
      </header>

      <section className={styles.grid}>
        <article className={styles.card}><h2>Health</h2><p>Status: {health?.status ?? '—'}</p><p>Composite: {health?.composite_score ?? '—'}</p></article>
        <article className={styles.card}><h2>Trends</h2><p>Points: {trends?.points?.length ?? 0}</p></article>
        <article className={styles.card}><h2>Quality</h2><p>Pass rate: {quality?.pass_rate ?? '—'}</p><p>Rules: {quality?.total_rules ?? '—'}</p></article>
        <article className={styles.card}><h2>KPIs</h2><p>Metrics: {kpis?.metrics?.length ?? 0}</p><p>Computed: {kpis?.computed_at ?? '—'}</p></article>
      </section>

      <section className={styles.card}>
        <h2>Narrative</h2>
        <p>{narrative?.summary ?? 'No narrative available.'}</p>
      </section>

      <section className={styles.grid}>
        <article className={styles.card}>
          <h2>Risks</h2>
          <ul>{risks.slice(0, 5).map((item) => <li key={item.id}>{item.title} · {item.severity ?? 'n/a'}</li>)}</ul>
        </article>
        <article className={styles.card}>
          <h2>Issues</h2>
          <ul>{issues.slice(0, 5).map((item) => <li key={item.id}>{item.title} · {item.status ?? 'n/a'}</li>)}</ul>
        </article>
        <article className={styles.card}>
          <h2>Approvals</h2>
          <ul>{filteredApprovals.map((item) => <li key={item.id ?? item.title}>{item.title}</li>)}</ul>
          <button onClick={() => navigate(`/approvals?project=${encodeURIComponent(projectId ?? '')}`)}>Open approvals</button>
        </article>
      </section>
    </div>
  );
}
