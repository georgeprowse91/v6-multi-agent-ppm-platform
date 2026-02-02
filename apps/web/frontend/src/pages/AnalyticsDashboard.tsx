import { useCallback, useEffect, useMemo, useState } from 'react';
import { hasPermission } from '@/auth/permissions';
import { useAppStore } from '@/store';
import styles from './AnalyticsDashboard.module.css';

interface TrendPoint {
  timestamp: string;
  value: number | null;
}

interface TrendSeries {
  metric: string;
  points: TrendPoint[];
  slope: number | null;
  forecast: number | null;
  forecast_method: string | null;
  recent_change: number | null;
}

interface TrendWarning {
  type: string;
  message: string;
  forecast?: number;
}

interface TrendResponse {
  project_id: string;
  computed_at: string;
  period_count: number;
  series: TrendSeries[];
  warnings: TrendWarning[];
}

const formatMetric = (metric: string) =>
  metric
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());

const formatValue = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : 'N/A';

const buildChartPath = (values: Array<number | null>, width = 320, height = 160) => {
  const points = values
    .map((value, index) => ({ value, index }))
    .filter((point) => point.value !== null) as Array<{ value: number; index: number }>;
  if (points.length < 2) return '';
  const min = Math.min(...points.map((point) => point.value));
  const max = Math.max(...points.map((point) => point.value));
  const range = max - min || 1;
  return points
    .map((point, idx) => {
      const x = (point.index / Math.max(values.length - 1, 1)) * width;
      const y = height - ((point.value - min) / range) * height;
      return `${idx === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
};

export function AnalyticsDashboard() {
  const { currentSelection, session } = useAppStore();
  const [projectId, setProjectId] = useState(
    currentSelection?.id ?? 'demo-project'
  );
  const [data, setData] = useState<TrendResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canViewAnalytics = hasPermission(session.user?.permissions, 'analytics.view');

  const loadTrends = useCallback(async () => {
    if (!canViewAnalytics) {
      setLoading(false);
      setError('You do not have permission to view analytics.');
      setData(null);
      return;
    }
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `/v1/api/analytics/trends?project_id=${encodeURIComponent(projectId)}`
      );
      if (!response.ok) {
        throw new Error(`Failed to load trends (${response.status})`);
      }
      const payload = (await response.json()) as TrendResponse;
      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load analytics trends.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [canViewAnalytics, projectId]);

  useEffect(() => {
    if (currentSelection?.id && currentSelection.id !== projectId) {
      setProjectId(currentSelection.id);
    }
  }, [currentSelection, projectId]);

  useEffect(() => {
    if (canViewAnalytics) {
      void loadTrends();
    } else {
      setLoading(false);
    }
  }, [canViewAnalytics, loadTrends]);

  const timestampLabels = useMemo(
    () => data?.series?.[0]?.points.map((point) => point.timestamp) ?? [],
    [data?.series]
  );

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Analytics Dashboard</h1>
          <p className={styles.subtitle}>
            KPI trends and forecasts over the last {data?.period_count ?? 6} periods.
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
          <button
            className={styles.button}
            type="button"
            onClick={loadTrends}
            disabled={loading || !canViewAnalytics}
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </header>

      {!canViewAnalytics && (
        <div className={styles.emptyState}>
          You do not have permission to view analytics dashboards.
        </div>
      )}

      {error && <div className={styles.emptyState}>{error}</div>}

      {canViewAnalytics && data?.warnings?.length ? (
        <div className={styles.warningPanel}>
          <div className={styles.warningTitle}>Predictive Warnings</div>
          {data.warnings.map((warning) => (
            <div key={warning.type} className={styles.warningItem}>
              {warning.message}{' '}
              {warning.forecast !== undefined ? `(${formatValue(warning.forecast)})` : ''}
            </div>
          ))}
        </div>
      ) : null}

      {canViewAnalytics && !loading && data?.series?.length ? (
        <div className={styles.grid}>
          {data.series.map((series) => (
            <div key={series.metric} className={styles.card}>
              <div className={styles.cardTitle}>{formatMetric(series.metric)}</div>
              <div className={styles.metricMeta}>
                <span>Trend: {formatValue(series.slope)}</span>
                <span>Forecast: {formatValue(series.forecast)}</span>
                <span>Recent change: {formatValue(series.recent_change)}</span>
              </div>
              <div className={styles.chart}>
                <svg viewBox="0 0 320 160" role="img" aria-label={`${series.metric} trend`}>
                  <path
                    d={buildChartPath(series.points.map((point) => point.value))}
                    fill="none"
                    stroke="#2563eb"
                    strokeWidth="3"
                  />
                </svg>
                <div className={styles.chartLabels}>
                  {timestampLabels.map((label, index) => (
                    <span key={`${series.metric}-${label}-${index}`}>
                      {new Date(label).toLocaleDateString()}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
