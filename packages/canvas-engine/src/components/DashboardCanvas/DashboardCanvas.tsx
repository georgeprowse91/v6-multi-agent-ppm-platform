/**
 * DashboardCanvas - Widget-based dashboard
 *
 * A placeholder dashboard with mock widgets.
 * Real charts and data binding will be added in a future iteration.
 */

import { useEffect, useMemo, useState } from 'react';
import type { CanvasComponentProps } from '../../types/canvas';
import type { DashboardContent, DashboardWidget } from '../../types/artifact';
import styles from './DashboardCanvas.module.css';

export interface DashboardCanvasProps extends CanvasComponentProps<DashboardContent> {
  unifiedDashboardsEnabled?: boolean;
}

const API_BASE = '/api/dashboard';

type HealthMetric = {
  score: number;
  status: string;
  raw?: number | null;
};

type ProjectHealth = {
  project_id: string;
  composite_score: number;
  health_status: string;
  metrics: Record<string, HealthMetric>;
  concerns: string[];
  warnings: { type?: string; message?: string }[];
  recommendations: string[];
  monitored_at: string;
};

type HealthTrendPoint = {
  timestamp: string;
  composite_score: number;
  metrics: Record<string, number>;
};

type QualitySummary = {
  average_score: number;
  total_events: number;
  by_entity: Record<string, number>;
};

type KpiMetric = {
  name: string;
  value: number | null;
  normalized: number;
};

type ProjectKpis = {
  project_id: string;
  metrics: KpiMetric[];
  computed_at: string;
};

type NarrativeResponse = {
  project_id: string;
  summary: string;
  highlights: string[];
  risks: string[];
  opportunities: string[];
  data_quality_notes: string[];
  computed_at: string;
};

type AggregatedArtifactMetric = {
  artifact_type: string;
  label: string;
  total: number;
  last_updated: string | null;
  owners: string[];
  status_breakdown: Record<string, number>;
  route: string;
  sample_ids: string[];
};

type LineageProvenance = {
  total_nodes: number;
  total_edges: number;
  source_systems: string[];
  target_schemas: string[];
  latest_event_at: string | null;
  average_quality_score: number | null;
  quality_event_count: number;
};

type AggregationResponse = {
  project_id: string;
  computed_at: string;
  artifacts: AggregatedArtifactMetric[];
  lineage: LineageProvenance | null;
  warnings: string[];
};

/** Mock chart component */
function MockChart({ type, title }: { type: string; title: string }) {
  return (
    <div className={styles.mockChart}>
      <div className={styles.chartHeader}>
        <span className={styles.chartTitle}>{title}</span>
        <span className={styles.chartType}>{type}</span>
      </div>
      <div className={styles.chartBody}>
        {type === 'bar' && (
          <div className={styles.barChart}>
            {[65, 80, 45, 90, 70].map((height, idx) => (
              <div
                key={idx}
                className={styles.bar}
                style={{ height: `${height}%` }}
              />
            ))}
          </div>
        )}
        {type === 'line' && (
          <svg className={styles.lineChart} viewBox="0 0 100 50" preserveAspectRatio="none">
            <polyline
              fill="none"
              stroke="var(--color-dataviz-series-primary)"
              strokeWidth="2"
              points="0,40 20,25 40,35 60,15 80,20 100,10"
            />
          </svg>
        )}
        {type === 'pie' && (
          <svg className={styles.pieChart} viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40" fill="var(--color-dataviz-series-secondary)" />
            <path
              d="M 50 50 L 50 10 A 40 40 0 0 1 85 65 Z"
              fill="var(--color-dataviz-series-primary)"
            />
            <path
              d="M 50 50 L 85 65 A 40 40 0 0 1 25 75 Z"
              fill="var(--color-dataviz-series-tertiary)"
            />
          </svg>
        )}
        {type === 'area' && (
          <svg className={styles.areaChart} viewBox="0 0 100 50" preserveAspectRatio="none">
            <path
              fill="var(--color-dataviz-series-secondary)"
              d="M 0,50 L 0,40 20,25 40,35 60,15 80,20 100,10 100,50 Z"
            />
            <polyline
              fill="none"
              stroke="var(--color-dataviz-series-primary)"
              strokeWidth="2"
              points="0,40 20,25 40,35 60,15 80,20 100,10"
            />
          </svg>
        )}
      </div>
    </div>
  );
}

function KPIWidget({
  label,
  score,
  status,
  helper,
}: {
  label: string;
  score: number;
  status: string;
  helper?: string;
}) {
  const scoreLabel = `${Math.round(score * 100)}%`;
  return (
    <div className={styles.kpiCard}>
      <div className={styles.kpiLabel}>{label}</div>
      <div className={styles.kpiValue}>
        {scoreLabel}
        <span className={`${styles.statusBadge} ${styles[status] || ''}`}>{status}</span>
      </div>
      {helper && <div className={styles.kpiHelper}>{helper}</div>}
    </div>
  );
}

function TrendLineChart({ points }: { points: HealthTrendPoint[] }) {
  const line = useMemo(() => {
    if (points.length < 2) {
      return '';
    }
    const values = points.map((point) => point.composite_score);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    return points
      .map((point, index) => {
        const x = (index / (points.length - 1)) * 100;
        const y = 40 - ((point.composite_score - min) / range) * 30;
        return `${x},${y}`;
      })
      .join(' ');
  }, [points]);

  if (points.length === 0) {
    return <div className={styles.emptyChart}>No trend data yet.</div>;
  }

  return (
    <svg className={styles.trendChart} viewBox="0 0 100 40" preserveAspectRatio="none">
      <polyline
        fill="none"
        stroke="var(--color-dataviz-series-primary)"
        strokeWidth="2"
        points={line}
      />
    </svg>
  );
}

/** Metric widget */
function MetricWidget({ title, config }: { title: string; config: Record<string, unknown> }) {
  const value = config.value as string | number || '—';
  const change = config.change as number | undefined;
  const unit = config.unit as string || '';

  return (
    <div className={styles.metric}>
      <span className={styles.metricLabel}>{title}</span>
      <span className={styles.metricValue}>
        {value}
        {unit && <span className={styles.metricUnit}>{unit}</span>}
      </span>
      {change !== undefined && (
        <span className={`${styles.metricChange} ${change >= 0 ? styles.positive : styles.negative}`}>
          {change >= 0 ? '↑' : '↓'} {Math.abs(change)}%
        </span>
      )}
    </div>
  );
}

/** Table widget */
function TableWidget({ title, config }: { title: string; config: Record<string, unknown> }) {
  const headers = (config.headers as string[]) || ['Column 1', 'Column 2', 'Column 3'];
  const rows = (config.rows as string[][]) || [
    ['Data 1', 'Data 2', 'Data 3'],
    ['Data 4', 'Data 5', 'Data 6'],
  ];

  return (
    <div className={styles.tableWidget}>
      <div className={styles.tableHeader}>{title}</div>
      <table className={styles.table}>
        <thead>
          <tr>
            {headers.map((h, idx) => (
              <th key={idx}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx}>
              {row.map((cell, cellIdx) => (
                <td key={cellIdx}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Text widget */
function TextWidget({ title, config }: { title: string; config: Record<string, unknown> }) {
  const content = (config.content as string) || 'No content';

  return (
    <div className={styles.textWidget}>
      <div className={styles.textHeader}>{title}</div>
      <div className={styles.textContent}>{content}</div>
    </div>
  );
}

/** Render a widget based on its type */
function renderWidget(widget: DashboardWidget) {
  switch (widget.type) {
    case 'chart':
      return (
        <MockChart
          title={widget.title}
          type={(widget.config.chartType as string) || 'bar'}
        />
      );
    case 'metric':
      return <MetricWidget title={widget.title} config={widget.config} />;
    case 'table':
      return <TableWidget title={widget.title} config={widget.config} />;
    case 'text':
      return <TextWidget title={widget.title} config={widget.config} />;
    default:
      return (
        <div className={styles.unknownWidget}>
          <span>Unknown widget type: {widget.type}</span>
        </div>
      );
  }
}

export function DashboardCanvas({
  artifact,
  className,
  unifiedDashboardsEnabled = false,
}: DashboardCanvasProps) {
  const { widgets, gridColumns = 12 } = artifact.content;
  const [health, setHealth] = useState<ProjectHealth | null>(null);
  const [trends, setTrends] = useState<HealthTrendPoint[]>([]);
  const [quality, setQuality] = useState<QualitySummary | null>(null);
  const [kpis, setKpis] = useState<ProjectKpis | null>(null);
  const [narrative, setNarrative] = useState<NarrativeResponse | null>(null);
  const [aggregations, setAggregations] = useState<AggregationResponse | null>(null);
  const [aggregationMessage, setAggregationMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [whatIfMessage, setWhatIfMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchHealth = async () => {
      setLoading(true);
      setError(null);
      try {
        const aggregationPromise = unifiedDashboardsEnabled
          ? fetch(`${API_BASE}/${artifact.projectId}/aggregations`)
          : Promise.resolve(null);
        const [
          healthResponse,
          trendResponse,
          qualityResponse,
          kpiResponse,
          narrativeResponse,
          aggregationResponse,
        ] = await Promise.all([
          fetch(`${API_BASE}/${artifact.projectId}/health`),
          fetch(`${API_BASE}/${artifact.projectId}/trends`),
          fetch(`${API_BASE}/${artifact.projectId}/quality`),
          fetch(`${API_BASE}/${artifact.projectId}/kpis`),
          fetch(`${API_BASE}/${artifact.projectId}/narrative`),
          aggregationPromise,
        ]);
        if (!healthResponse.ok) {
          throw new Error('Unable to load project health.');
        }
        const healthData = (await healthResponse.json()) as ProjectHealth;
        const trendsData = trendResponse.ok
          ? ((await trendResponse.json()) as { points?: HealthTrendPoint[] })
          : { points: [] };
        const qualityData = qualityResponse.ok
          ? ((await qualityResponse.json()) as QualitySummary)
          : null;
        const kpiData = kpiResponse.ok ? ((await kpiResponse.json()) as ProjectKpis) : null;
        const narrativeData = narrativeResponse.ok
          ? ((await narrativeResponse.json()) as NarrativeResponse)
          : null;
        let aggregationData: AggregationResponse | null = null;
        let aggregationNote: string | null = null;
        if (aggregationResponse) {
          if (aggregationResponse.ok) {
            aggregationData = (await aggregationResponse.json()) as AggregationResponse;
          } else if (aggregationResponse.status !== 404) {
            aggregationNote = 'Unable to load aggregation metrics.';
          }
        }
        if (isMounted) {
          setHealth(healthData);
          setTrends(trendsData.points ?? []);
          setQuality(qualityData);
          setKpis(kpiData);
          setNarrative(narrativeData);
          setAggregations(aggregationData);
          setAggregationMessage(aggregationNote);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Unable to load dashboard data.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    fetchHealth();
    return () => {
      isMounted = false;
    };
  }, [artifact.projectId, unifiedDashboardsEnabled]);

  const buildArtifactLink = (route: string, artifactId: string) => {
    if (route.includes('?')) {
      return `${route}&artifact_id=${artifactId}`;
    }
    return `${route}?artifact_id=${artifactId}`;
  };

  const handleExport = () => {
    if (!health) {
      return;
    }
    const metricRows = Object.entries(health.metrics).map(([key, metric]) => [
      key,
      (metric.score * 100).toFixed(1),
      metric.status,
      metric.raw ?? '',
    ]);
    const rows = [
      ['Project ID', health.project_id],
      ['Monitored At', health.monitored_at],
      ['Composite Score', (health.composite_score * 100).toFixed(1)],
      [],
      ['Metric', 'Score (%)', 'Status', 'Raw'],
      ...metricRows,
    ];
    const csv = rows.map((row) => row.map(String).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `project-${health.project_id}-health.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const handleWhatIf = async () => {
    setWhatIfMessage(null);
    try {
      const response = await fetch(
        `${API_BASE}/${artifact.projectId}/what-if`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scenario: 'resource_boost',
            adjustments: { resource_delta: 2 },
          }),
        }
      );
      if (!response.ok) {
        throw new Error('Unable to request what-if scenario.');
      }
      const data = (await response.json()) as { message?: string };
      setWhatIfMessage(data.message ?? 'What-if analysis queued.');
    } catch (err) {
      setWhatIfMessage(err instanceof Error ? err.message : 'Unable to request what-if scenario.');
    }
  };

  // If no widgets, show empty state
  if (!loading && widgets.length === 0 && !health && !kpis) {
    return (
      <div className={`${styles.container} ${className ?? ''}`}>
        <div className={styles.emptyState}>
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="3" width="7" height="9" rx="1" />
            <rect x="14" y="3" width="7" height="5" rx="1" />
            <rect x="14" y="12" width="7" height="9" rx="1" />
            <rect x="3" y="16" width="7" height="5" rx="1" />
          </svg>
          <h3>No widgets yet</h3>
          <p>Add charts, metrics, and tables to build your dashboard.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.container} ${className ?? ''}`}>
      <div className={styles.dashboardHeader}>
        <div>
          <h2 className={styles.dashboardTitle}>Project Health Dashboard</h2>
          <p className={styles.dashboardSubtitle}>
            {health
              ? `Updated ${
                  health.monitored_at
                    ? new Date(health.monitored_at).toLocaleString()
                    : 'recently'
                }`
              : 'Fetching project health insights...'}
          </p>
        </div>
        <div className={styles.dashboardActions}>
          <button className={styles.secondaryButton} type="button" onClick={handleWhatIf}>
            What-if Analysis
          </button>
          <button className={styles.primaryButton} type="button" onClick={handleExport}>
            Export CSV
          </button>
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      <div className={styles.kpiGrid}>
        {health && (
          <>
            <div className={styles.kpiCardWide}>
              <div className={styles.kpiLabel}>Overall Health</div>
              <div className={styles.kpiValueLarge}>
                {Math.round(health.composite_score * 100)}%
                <span className={styles.healthStatus}>{health.health_status}</span>
              </div>
              <div className={styles.kpiHelper}>
                {health.concerns.length} active concerns · {health.warnings.length} warnings
              </div>
            </div>
            <KPIWidget
              label="Schedule"
              score={health.metrics.schedule?.score ?? 0}
              status={health.metrics.schedule?.status ?? 'unknown'}
            />
            <KPIWidget
              label="Cost"
              score={health.metrics.cost?.score ?? 0}
              status={health.metrics.cost?.status ?? 'unknown'}
            />
            <KPIWidget
              label="Risk"
              score={health.metrics.risk?.score ?? 0}
              status={health.metrics.risk?.status ?? 'unknown'}
            />
            <KPIWidget
              label="Resource"
              score={health.metrics.resource?.score ?? 0}
              status={health.metrics.resource?.status ?? 'unknown'}
            />
          </>
        )}
        {!health && loading && <div className={styles.loadingCard}>Loading KPIs...</div>}
        {kpis && !loading && (
          <div className={styles.kpiCardWide}>
            <div className={styles.kpiLabel}>Key Metrics</div>
            <div className={styles.kpiMetricList}>
              {kpis.metrics.slice(0, 4).map((metric) => (
                <div key={metric.name} className={styles.kpiMetricRow}>
                  <span>{metric.name}</span>
                  <strong>{metric.value ?? '—'}</strong>
                </div>
              ))}
            </div>
            <div className={styles.kpiHelper}>
              Computed {new Date(kpis.computed_at).toLocaleString()}
            </div>
          </div>
        )}
      </div>

      <div className={styles.trendGrid}>
        <div className={styles.widgetContainer}>
          <div className={styles.sectionHeader}>
            <h3>Health Trend</h3>
            <span>Composite score (last {trends.length} snapshots)</span>
          </div>
          <div className={styles.sectionBody}>
            <TrendLineChart points={trends} />
          </div>
        </div>
        <div className={styles.widgetContainer}>
          <div className={styles.sectionHeader}>
            <h3>Concerns & Warnings</h3>
            <span>Signals requiring attention</span>
          </div>
          <div className={styles.sectionBody}>
            <ul className={styles.list}>
              {health?.concerns.map((concern) => (
                <li key={concern}>{concern}</li>
              ))}
              {health?.warnings.map((warning, index) => (
                <li key={`warn-${index}`}>{warning.message ?? warning.type}</li>
              ))}
              {!health?.concerns.length && !health?.warnings.length && (
                <li>No active concerns.</li>
              )}
            </ul>
          </div>
        </div>
      </div>

      <div className={styles.trendGrid}>
        <div className={styles.widgetContainer}>
          <div className={styles.sectionHeader}>
            <h3>Recommendations</h3>
            <span>Suggested next steps</span>
          </div>
          <div className={styles.sectionBody}>
            <ul className={styles.list}>
              {health?.recommendations.map((rec) => (
                <li key={rec}>{rec}</li>
              ))}
              {!health?.recommendations.length && <li>No recommendations available.</li>}
            </ul>
          </div>
        </div>
        <div className={styles.widgetContainer}>
          <div className={styles.sectionHeader}>
            <h3>Scenario Feedback</h3>
            <span>What-if analysis status</span>
          </div>
          <div className={styles.sectionBody}>
            <p className={styles.statusMessage}>
              {whatIfMessage ?? 'Run a what-if scenario to explore improvement options.'}
            </p>
          </div>
        </div>
      </div>

      {unifiedDashboardsEnabled && (
        <div className={styles.trendGrid}>
          <div className={styles.widgetContainer}>
            <div className={styles.sectionHeader}>
              <h3>Cross-artefact Metrics</h3>
              <span>Counts and owners by artefact type</span>
            </div>
            <div className={styles.sectionBody}>
              {aggregationMessage && (
                <p className={styles.statusMessage}>{aggregationMessage}</p>
              )}
              {aggregations ? (
                <div className={styles.artifactList}>
                  {aggregations.artifacts.map((item) => (
                    <div key={item.artifact_type} className={styles.artifactRow}>
                      <div className={styles.artifactHeader}>
                        <div className={styles.artifactTitle}>
                          <strong>{item.label}</strong>
                          <span className={styles.artifactCount}>{item.total}</span>
                        </div>
                        <a className={styles.artifactLink} href={item.route}>
                          Open
                        </a>
                      </div>
                      <div className={styles.artifactMeta}>
                        <span>
                          Last updated:{' '}
                          {item.last_updated
                            ? new Date(item.last_updated).toLocaleString()
                            : 'n/a'}
                        </span>
                        <span>
                          Owners: {item.owners.length ? item.owners.join(', ') : 'Unassigned'}
                        </span>
                      </div>
                      <div className={styles.artifactMeta}>
                        Status mix:{' '}
                        {Object.entries(item.status_breakdown).length
                          ? Object.entries(item.status_breakdown)
                              .map(([status, count]) => `${status} (${count})`)
                              .join(' · ')
                          : 'No statuses'}
                      </div>
                      {item.sample_ids.length > 0 && (
                        <div className={styles.artifactLinks}>
                          {item.sample_ids.slice(0, 3).map((artifactId) => (
                            <a
                              key={artifactId}
                              className={styles.artifactLinkSecondary}
                              href={buildArtifactLink(item.route, artifactId)}
                            >
                              View {artifactId}
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                  {aggregations.warnings.length > 0 && (
                    <div className={styles.warningList}>
                      {aggregations.warnings.map((warning, index) => (
                        <span key={`agg-warning-${index}`}>{warning}</span>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <p className={styles.statusMessage}>Aggregation metrics are loading.</p>
              )}
            </div>
          </div>
          <div className={styles.widgetContainer}>
            <div className={styles.sectionHeader}>
              <h3>Lineage Provenance</h3>
              <span>Upstream sources & quality signals</span>
            </div>
            <div className={styles.sectionBody}>
              {aggregations?.lineage ? (
                <div className={styles.provenanceGrid}>
                  <div>
                    <div className={styles.provenanceLabel}>Nodes</div>
                    <div className={styles.provenanceValue}>
                      {aggregations.lineage.total_nodes}
                    </div>
                  </div>
                  <div>
                    <div className={styles.provenanceLabel}>Edges</div>
                    <div className={styles.provenanceValue}>
                      {aggregations.lineage.total_edges}
                    </div>
                  </div>
                  <div>
                    <div className={styles.provenanceLabel}>Latest event</div>
                    <div className={styles.provenanceValue}>
                      {aggregations.lineage.latest_event_at
                        ? new Date(aggregations.lineage.latest_event_at).toLocaleString()
                        : 'n/a'}
                    </div>
                  </div>
                  <div>
                    <div className={styles.provenanceLabel}>Avg quality</div>
                    <div className={styles.provenanceValue}>
                      {aggregations.lineage.average_quality_score !== null
                        ? `${Math.round(aggregations.lineage.average_quality_score * 100)}%`
                        : 'n/a'}
                    </div>
                  </div>
                  <div className={styles.provenanceSpan}>
                    <div className={styles.provenanceLabel}>Source systems</div>
                    <div className={styles.provenanceValue}>
                      {aggregations.lineage.source_systems.length
                        ? aggregations.lineage.source_systems.join(', ')
                        : 'None reported'}
                    </div>
                  </div>
                  <div className={styles.provenanceSpan}>
                    <div className={styles.provenanceLabel}>Target schemas</div>
                    <div className={styles.provenanceValue}>
                      {aggregations.lineage.target_schemas.length
                        ? aggregations.lineage.target_schemas.join(', ')
                        : 'None reported'}
                    </div>
                  </div>
                </div>
              ) : (
                <p className={styles.statusMessage}>Lineage provenance not yet available.</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className={styles.trendGrid}>
        <div className={styles.widgetContainer}>
          <div className={styles.sectionHeader}>
            <h3>Quality Overview</h3>
            <span>Data lineage and monitoring</span>
          </div>
          <div className={styles.sectionBody}>
            {quality ? (
              <>
                <p className={styles.statusMessage}>
                  Average quality score: <strong>{Math.round(quality.average_score * 100)}%</strong>
                </p>
                <p className={styles.statusMessage}>
                  {quality.total_events} quality signals analyzed.
                </p>
                <ul className={styles.list}>
                  {Object.entries(quality.by_entity).map(([entity, score]) => (
                    <li key={entity}>
                      {entity}: {Math.round(score * 100)}%
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className={styles.statusMessage}>Quality metrics not yet available.</p>
            )}
          </div>
        </div>
        <div className={styles.widgetContainer}>
          <div className={styles.sectionHeader}>
            <h3>Executive Narrative</h3>
            <span>AI-generated project brief</span>
          </div>
          <div className={styles.sectionBody}>
            {narrative ? (
              <>
                <p className={styles.statusMessage}>{narrative.summary}</p>
                <ul className={styles.list}>
                  {narrative.highlights.slice(0, 3).map((highlight) => (
                    <li key={highlight}>{highlight}</li>
                  ))}
                  {narrative.risks.slice(0, 2).map((risk) => (
                    <li key={risk}>Risk: {risk}</li>
                  ))}
                  {narrative.opportunities.slice(0, 2).map((item) => (
                    <li key={item}>Opportunity: {item}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p className={styles.statusMessage}>Narrative insights are loading.</p>
            )}
          </div>
        </div>
      </div>

      {widgets.length > 0 && !health && !loading && (
        <div
          className={styles.grid}
          style={{
            gridTemplateColumns: `repeat(${gridColumns}, 1fr)`,
          }}
        >
          {widgets.map(widget => (
            <div
              key={widget.id}
              className={styles.widgetContainer}
              style={{
                gridColumn: `${widget.x + 1} / span ${widget.width}`,
                gridRow: `${widget.y + 1} / span ${widget.height}`,
              }}
            >
              {renderWidget(widget)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
