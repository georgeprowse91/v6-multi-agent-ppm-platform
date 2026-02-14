import { useEffect, useMemo, useState } from 'react';
import styles from './DemoRunPage.module.css';

type AgentExecution = {
  agent_id: string;
  status: string;
  duration_seconds: number;
  artifacts: string[];
};

type DemoRunLog = {
  demo_run_id: string;
  started_at: string;
  total_agents_executed: number;
  agents: AgentExecution[];
};


type SorState = {
  outbox: Array<Record<string, unknown>>;
  applied_changes: Array<Record<string, unknown>>;
};

const DEMO_LOG_PATHS = [
  '/data/demo/demo_run_log.json',
  '/demo/demo_run_log.json',
  '/v1/demo/run-log',
] as const;

export function DemoRunPage() {
  const [demoRunLog, setDemoRunLog] = useState<DemoRunLog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sorState, setSorState] = useState<SorState>({ outbox: [], applied_changes: [] });

  useEffect(() => {
    let mounted = true;

    const loadDemoRunLog = async () => {
      try {
        let loaded: DemoRunLog | null = null;

        for (const path of DEMO_LOG_PATHS) {
          const response = await fetch(path);
          if (!response.ok) continue;
          loaded = (await response.json()) as DemoRunLog;
          break;
        }

        if (!loaded) {
          throw new Error('Unable to load demo run log data.');
        }

        const sorResponse = await fetch("/v1/api/demo/sor");
        if (sorResponse.ok) {
          setSorState((await sorResponse.json()) as SorState);
        }

        if (mounted) {
          setDemoRunLog(loaded);
          setError(null);
        }
      } catch (loadError) {
        if (mounted) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load demo run log data.');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    void loadDemoRunLog();

    return () => {
      mounted = false;
    };
  }, []);

  const timelineRows = useMemo(() => {
    if (!demoRunLog?.agents.length) return [];

    const maxDuration = Math.max(...demoRunLog.agents.map((agent) => agent.duration_seconds));
    return demoRunLog.agents.map((agent) => ({
      ...agent,
      widthPct: Math.max(8, Math.round((agent.duration_seconds / maxDuration) * 100)),
    }));
  }, [demoRunLog]);

  if (loading) {
    return <div className={styles.state}>Loading demo run activity…</div>;
  }

  if (error || !demoRunLog) {
    return <div className={styles.stateError}>{error ?? 'Demo run data unavailable.'}</div>;
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Demo Run</h1>
        <p className={styles.subtitle}>Run ID: {demoRunLog.demo_run_id}</p>
      </header>

      <section className={styles.card}>
        <h2>Total agents executed</h2>
        <p className={styles.totalAgents}>{demoRunLog.total_agents_executed}</p>
      </section>

      <section className={styles.card}>
        <h2>Agent Activity</h2>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Agent ID</th>
              <th>Status</th>
              <th>Duration (s)</th>
              <th>Artifacts</th>
            </tr>
          </thead>
          <tbody>
            {demoRunLog.agents.map((agent) => (
              <tr key={agent.agent_id}>
                <td>{agent.agent_id}</td>
                <td>{agent.status}</td>
                <td>{agent.duration_seconds}</td>
                <td>{agent.artifacts.length ? agent.artifacts.join(', ') : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className={styles.card}>
        <h2>SoR outbox</h2>
        <p>Outbox entries: {sorState.outbox.length}</p>
        <p>Applied changes: {sorState.applied_changes.length}</p>
      </section>

      <section className={styles.card}>
        <h2>Execution timeline</h2>
        <ul className={styles.timeline}>
          {timelineRows.map((agent) => (
            <li key={`timeline-${agent.agent_id}`} className={styles.timelineRow}>
              <span className={styles.timelineLabel}>{agent.agent_id}</span>
              <div className={styles.timelineTrack}>
                <span className={styles.timelineBar} style={{ width: `${agent.widthPct}%` }} />
              </div>
              <span className={styles.timelineDuration}>{agent.duration_seconds}s</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export default DemoRunPage;
