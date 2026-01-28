import { useEffect, useState } from 'react';
import styles from './SyncStatusPanel.module.css';

interface SyncSummary {
  connector: string;
  entity: string;
  total_runs: number;
  success_runs: number;
  error_runs: number;
  success_rate: number;
  last_sync_at: string | null;
  last_status: string | null;
}

const API_BASE = '/api/v1';

const mockSummary: SyncSummary[] = [
  {
    connector: 'jira',
    entity: 'tasks',
    total_runs: 8,
    success_runs: 7,
    error_runs: 1,
    success_rate: 0.88,
    last_sync_at: new Date().toISOString(),
    last_status: 'success',
  },
];

export function SyncStatusPanel() {
  const [summary, setSummary] = useState<SyncSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/sync/summary`);
      if (!response.ok) {
        throw new Error('Failed to load sync summary');
      }
      const data = (await response.json()) as SyncSummary[];
      setSummary(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      setSummary(mockSummary);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Sync Status</h2>
          <p className={styles.subtitle}>Track connector sync health and latest runs.</p>
        </div>
        <button className={styles.refreshButton} onClick={fetchSummary}>
          Refresh
        </button>
      </div>

      {loading && <div className={styles.loading}>Loading sync status...</div>}
      {error && !loading && <div className={styles.error}>{error}</div>}

      {!loading && summary.length > 0 && (
        <div className={styles.grid}>
          {summary.map((item) => {
            const successRate = Math.round(item.success_rate * 100);
            const badgeClass =
              item.last_status === 'error' ? `${styles.statusBadge} ${styles.statusError}` : styles.statusBadge;
            return (
              <div className={styles.card} key={`${item.connector}-${item.entity}`}>
                <div className={styles.cardHeader}>
                  <span className={styles.connectorName}>
                    {item.connector.toUpperCase()} · {item.entity}
                  </span>
                  <span className={badgeClass}>{item.last_status ?? 'idle'}</span>
                </div>
                <div className={styles.metrics}>
                  <span>Last sync: {item.last_sync_at ? new Date(item.last_sync_at).toLocaleString() : '—'}</span>
                  <span>Success rate: {successRate}%</span>
                  <span>Errors: {item.error_runs}</span>
                  <span>Total runs: {item.total_runs}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
