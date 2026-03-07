import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { hasPermission } from '@/auth/permissions';
import { useAppStore } from '@/store';
import { parseJsonResponse } from '@/utils/apiValidation';
import { Skeleton } from '@/components/ui/Skeleton';
import { ScenarioBuilder } from '@/components/analytics/ScenarioBuilder';
import { s } from '@/utils/schema';
import styles from './AnalyticsDashboard.module.css';

interface TrendPoint {
  timestamp: string;
  value: number | null | undefined;
}

interface TrendSeries {
  metric: string;
  points: TrendPoint[];
  slope: number | null | undefined;
  forecast: number | null | undefined;
  forecast_method: string | null | undefined;
  recent_change: number | null | undefined;
}

interface TrendWarning {
  type: string;
  message: string;
  forecast?: number;
}

interface PredictiveAlertLink {
  label: string;
  url: string;
}

interface PredictiveAlert {
  alert_id: string;
  project_id: string;
  agent_id: string;
  metric: string;
  percentile: number;
  severity?: string | null;
  rationale: string;
  mitigations: string[];
  links: PredictiveAlertLink[];
  detected_at: string;
}

interface TrendResponse {
  project_id: string;
  computed_at: string;
  period_count: number;
  series: TrendSeries[];
  warnings: TrendWarning[];
}

const trendResponseSchema = s.object({
  project_id: s.string(),
  computed_at: s.string(),
  period_count: s.number(),
  series: s.array(
    s.object({
      metric: s.string(),
      points: s.array(s.object({ timestamp: s.string(), value: s.number().nullish() })),
      slope: s.number().nullish(),
      forecast: s.number().nullish(),
      forecast_method: s.string().nullish(),
      recent_change: s.number().nullish(),
    })
  ),
  warnings: s.array(
    s.object({
      type: s.string(),
      message: s.string(),
      forecast: s.number().optional(),
    })
  ),
});

const predictiveAlertSchema = s.object({
  alert_id: s.string(),
  project_id: s.string(),
  agent_id: s.string(),
  metric: s.string(),
  percentile: s.number(),
  severity: s.string().nullish(),
  rationale: s.string(),
  mitigations: s.array(s.string()),
  links: s.array(s.object({ label: s.string(), url: s.string() })),
  detected_at: s.string(),
});

const formatMetric = (metric: string) =>
  metric
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());

const formatValue = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : 'N/A';

const formatPercentile = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? `${value.toFixed(1)}th percentile`
    : 'N/A';

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
  const { currentSelection, session, featureFlags } = useAppStore();
  const [searchParams] = useSearchParams();
  const projectFromQuery = searchParams.get('project');
  const [projectId, setProjectId] = useState(
    projectFromQuery ?? currentSelection?.id ?? 'demo-project'
  );
  const [data, setData] = useState<TrendResponse | null>(null);
  const [predictiveAlerts, setPredictiveAlerts] = useState<PredictiveAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'trends' | 'scenarios'>('trends');
  const canViewAnalytics = hasPermission(session.user?.permissions, 'analytics.view');
  const predictiveAlertsEnabled = featureFlags.predictive_alerts === true;
  const scenarioModelingEnabled = featureFlags.scenario_modeling !== false;

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
      const payload = await parseJsonResponse(
        response,
        trendResponseSchema,
        'analytics trends response'
      );
      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load analytics trends.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [canViewAnalytics, projectId]);

  useEffect(() => {
    if (projectFromQuery) {
      if (projectFromQuery !== projectId) {
        setProjectId(projectFromQuery);
      }
      return;
    }

    if (currentSelection?.id && currentSelection.id !== projectId) {
      setProjectId(currentSelection.id);
    }
  }, [currentSelection, projectFromQuery, projectId]);

  useEffect(() => {
    if (canViewAnalytics) {
      void loadTrends();
    } else {
      setLoading(false);
    }
  }, [canViewAnalytics, loadTrends]);

  const loadPredictiveAlerts = useCallback(async () => {
    if (!canViewAnalytics || !predictiveAlertsEnabled) {
      setPredictiveAlerts([]);
      return;
    }
    if (!projectId) return;
    try {
      const response = await fetch(
        `/v1/api/analytics/predictive-alerts?project_id=${encodeURIComponent(projectId)}`
      );
      if (!response.ok) {
        throw new Error(`Failed to load predictive alerts (${response.status})`);
      }
      const payload = await parseJsonResponse(
        response,
        s.array(predictiveAlertSchema),
        'analytics predictive alerts response'
      );
      setPredictiveAlerts(payload);
    } catch (err) {
      console.error(err);
      setPredictiveAlerts([]);
    }
  }, [canViewAnalytics, predictiveAlertsEnabled, projectId]);

  useEffect(() => {
    void loadPredictiveAlerts();
  }, [loadPredictiveAlerts]);

  const timestampLabels = useMemo(
    () => data?.series?.[0]?.points.map((point) => point.timestamp) ?? [],
    [data?.series]
  );

  const alertsByMetric = useMemo(() => {
    const map = new Map<string, PredictiveAlert>();
    predictiveAlerts.forEach((alert) => {
      if (!map.has(alert.metric)) {
        map.set(alert.metric, alert);
      }
    });
    return map;
  }, [predictiveAlerts]);

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Analytics Dashboard</h1>
          <p className={styles.subtitle}>
            {activeTab === 'trends'
              ? `KPI trends and forecasts over the last ${data?.period_count ?? 6} periods.`
              : 'Run what-if scenario analyses with preset templates or custom parameters.'}
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
            Refresh
          </button>
        </div>
      </header>

      {canViewAnalytics && scenarioModelingEnabled && (
        <div className={styles.tabBar}>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'trends' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('trends')}
          >
            KPI Trends
          </button>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'scenarios' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('scenarios')}
          >
            What-If Scenarios
          </button>
        </div>
      )}

      {!canViewAnalytics && (
        <div className={styles.emptyState}>
          You do not have permission to view analytics dashboards.
        </div>
      )}

      {error && <div className={styles.emptyState}>{error}</div>}

      {canViewAnalytics && activeTab === 'scenarios' && scenarioModelingEnabled && (
        <ScenarioBuilder projectId={projectId} />
      )}

      {activeTab === 'trends' && canViewAnalytics && data?.warnings?.length ? (
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

      {activeTab === 'trends' && canViewAnalytics && loading ? (
        <div className={styles.grid} aria-busy="true" aria-live="off">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={`analytics-skeleton-${index}`} className={styles.card}>
              <Skeleton variant="text" width="38%" />
              <div className={styles.metricMeta}>
                <Skeleton variant="text" width="28%" />
                <Skeleton variant="text" width="32%" />
                <Skeleton variant="text" width="30%" />
              </div>
              <Skeleton variant="chart" className={styles.analyticsChartSkeleton} />
            </div>
          ))}
        </div>
      ) : null}

      {activeTab === 'trends' && canViewAnalytics && !loading && data?.series?.length ? (
        <div className={styles.grid} aria-live="polite">
          {data.series.map((series) => {
            const alert = alertsByMetric.get(series.metric);
            return (
              <div key={series.metric} className={styles.card}>
                {predictiveAlertsEnabled && alert ? (
                <div className={styles.alertBadge}>Predictive alert</div>
                ) : null}
                <div className={styles.cardTitle}>{formatMetric(series.metric)}</div>
                <div className={styles.metricMeta}>
                  <span>Trend: {formatValue(series.slope)}</span>
                  <span>Forecast: {formatValue(series.forecast)}</span>
                  <span>Recent change: {formatValue(series.recent_change)}</span>
                </div>
                {predictiveAlertsEnabled ? (
                  <div className={styles.alertSection}>
                    {alert ? (
                      <>
                        <div className={styles.alertMeta}>
                          <span>Percentile: {formatPercentile(alert.percentile)}</span>
                          {alert.severity ? <span>Severity: {alert.severity}</span> : null}
                        </div>
                        <div className={styles.alertLabel}>Mitigations</div>
                        {alert.mitigations?.length ? (
                          <ul className={styles.mitigationList}>
                            {alert.mitigations.map((item, index) => (
                              <li key={`${series.metric}-mitigation-${index}`}>{item}</li>
                            ))}
                          </ul>
                        ) : (
                          <div className={styles.mitigationEmpty}>
                            No mitigations suggested yet.
                          </div>
                        )}
                      </>
                    ) : (
                      <div className={styles.mitigationEmpty}>
                        No predictive alerts for this metric.
                      </div>
                    )}
                  </div>
                ) : null}
                <div className={styles.chart}>
                  <svg viewBox="0 0 320 160" role="img" aria-label={`${series.metric} trend`}>
                    <path
                      d={buildChartPath(series.points.map((point) => point.value ?? null))}
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
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

export default AnalyticsDashboard;
