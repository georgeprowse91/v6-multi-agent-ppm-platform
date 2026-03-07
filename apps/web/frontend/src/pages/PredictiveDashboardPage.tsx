import { useCallback, useEffect, useState } from 'react';
import { requestJson } from '@/services/apiClient';
import { HealthBadge } from '@/components/dashboard/HealthBadge';
import styles from './PredictiveDashboardPage.module.css';

interface HealthPrediction {
  project_id: string;
  project_name: string;
  current_health_score: number;
  predicted_health_30d: number;
  predicted_health_60d: number;
  predicted_health_90d: number;
  risk_signal: number;
  schedule_signal: number;
  budget_signal: number;
  resource_signal: number;
  trend: string;
}

interface RiskHeatmapCell {
  project_id: string;
  project_name: string;
  risk_category: string;
  risk_score: number;
  trend: string;
}

interface BottleneckPrediction {
  resource_type: string;
  skill_area: string;
  severity: string;
  demand_capacity_ratio: number;
  bottleneck_start_date: string;
  bottleneck_end_date: string;
}

interface DerivedHealthAlert {
  alert_id: string;
  project_id: string;
  project_name: string;
  severity: string;
  trigger: string;
  message: string;
  current_score: number;
}

function riskColor(score: number): string {
  if (score >= 0.7) return '#ef4444';
  if (score >= 0.4) return '#eab308';
  return '#22c55e';
}

function trendArrow(trend: string): string {
  if (trend === 'improving' || trend === 'down') return '\u2193';
  if (trend === 'declining' || trend === 'up') return '\u2191';
  return '\u2192';
}

function alertSeverityClass(severity: string): string {
  if (severity === 'critical') return styles['severity-critical'];
  if (severity === 'warning') return styles['severity-high'];
  return styles['severity-low'];
}

function deriveAlerts(predictions: HealthPrediction[]): DerivedHealthAlert[] {
  return predictions
    .filter(p => p.current_health_score < 0.6 || p.trend === 'declining' || p.trend === 'rapidly_declining')
    .map(p => ({
      alert_id: `alert-${p.project_id}`,
      project_id: p.project_id,
      project_name: p.project_name,
      severity: p.current_health_score < 0.4 ? 'critical' : 'warning',
      trigger: p.trend === 'declining' || p.trend === 'rapidly_declining' ? 'declining_trend' : 'below_threshold',
      message: p.current_health_score < 0.4
        ? `Critical: ${p.project_name} health at ${Math.round(p.current_health_score * 100)}%`
        : `Warning: ${p.project_name} trending to ${Math.round(p.predicted_health_30d * 100)}% in 30d`,
      current_score: p.current_health_score,
    }));
}

export default function PredictiveDashboardPage() {
  const [health, setHealth] = useState<HealthPrediction[]>([]);
  const [heatmap, setHeatmap] = useState<RiskHeatmapCell[]>([]);
  const [bottlenecks, setBottlenecks] = useState<BottleneckPrediction[]>([]);
  const [alerts, setAlerts] = useState<DerivedHealthAlert[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [h, r, b] = await Promise.all([
        requestJson<HealthPrediction[]>('/v1/predictive/health-forecast?portfolio_id=default'),
        requestJson<RiskHeatmapCell[]>('/v1/predictive/risk-heatmap?portfolio_id=default'),
        requestJson<BottleneckPrediction[]>('/v1/predictive/resource-bottlenecks?portfolio_id=default'),
      ]);
      setHealth(h);
      setHeatmap(r);
      setBottlenecks(b);
      setAlerts(deriveAlerts(h));
    } catch {
      // demo fallback
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const riskCategories = [...new Set(heatmap.map(c => c.risk_category))];
  const projects = [...new Set(heatmap.map(c => c.project_name))];

  const criticalCount = health.filter(p => p.current_health_score < 0.4).length;
  const atRiskCount = health.filter(p => p.current_health_score >= 0.4 && p.current_health_score < 0.7).length;
  const healthyCount = health.filter(p => p.current_health_score >= 0.7).length;
  const decliningCount = health.filter(p => p.trend === 'declining' || p.trend === 'rapidly_declining').length;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Predictive Intelligence Dashboard</h1>
        <button className={styles.refreshBtn} onClick={fetchData} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </header>

      {/* Portfolio Health Summary */}
      {health.length > 0 && (
        <div className={styles.summaryRow}>
          <div className={styles.summaryCard}>
            <span className={styles.summaryValue}>{health.length}</span>
            <span className={styles.summaryLabel}>Projects tracked</span>
          </div>
          <div className={`${styles.summaryCard} ${criticalCount > 0 ? styles.summaryDanger : ''}`}>
            <span className={styles.summaryValue}>{criticalCount}</span>
            <span className={styles.summaryLabel}>Critical</span>
          </div>
          <div className={`${styles.summaryCard} ${atRiskCount > 0 ? styles.summaryWarning : ''}`}>
            <span className={styles.summaryValue}>{atRiskCount}</span>
            <span className={styles.summaryLabel}>At risk</span>
          </div>
          <div className={styles.summaryCard}>
            <span className={styles.summaryValue}>{healthyCount}</span>
            <span className={styles.summaryLabel}>Healthy</span>
          </div>
          <div className={`${styles.summaryCard} ${decliningCount > 0 ? styles.summaryWarning : ''}`}>
            <span className={styles.summaryValue}>{decliningCount}</span>
            <span className={styles.summaryLabel}>Declining trend</span>
          </div>
        </div>
      )}

      {/* Active Health Alerts */}
      {alerts.length > 0 && (
        <section className={styles.alertsSection}>
          <h2 className={styles.alertsHeading}>Active Health Alerts</h2>
          <div className={styles.alertsList}>
            {alerts.map(alert => (
              <div key={alert.alert_id} className={`${styles.alertItem} ${alertSeverityClass(alert.severity)}`}>
                <span className={`${styles.severityBadge} ${alertSeverityClass(alert.severity)}`}>
                  {alert.severity}
                </span>
                <span className={styles.alertMessage}>{alert.message}</span>
                <HealthBadge score={alert.current_score} size="sm" showTooltip={false} />
              </div>
            ))}
          </div>
        </section>
      )}

      <div className={styles.grid}>
        {/* Health Forecast */}
        <section className={styles.card}>
          <h2>Health Forecast</h2>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Project</th>
                <th>Current</th>
                <th>30d</th>
                <th>60d</th>
                <th>90d</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              {health.map(h => (
                <tr key={h.project_id}>
                  <td>{h.project_name}</td>
                  <td>
                    <HealthBadge
                      score={h.current_health_score}
                      trend={h.trend}
                      breakdown={{
                        risk_score: h.risk_signal,
                        schedule_score: h.schedule_signal,
                        budget_score: h.budget_signal,
                        resource_score: h.resource_signal,
                      }}
                      size="sm"
                    />
                  </td>
                  <td><HealthBadge score={h.predicted_health_30d} size="sm" showTooltip={false} /></td>
                  <td><HealthBadge score={h.predicted_health_60d} size="sm" showTooltip={false} /></td>
                  <td><HealthBadge score={h.predicted_health_90d} size="sm" showTooltip={false} /></td>
                  <td className={styles.trend}>{trendArrow(h.trend)} {h.trend}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Risk Heatmap */}
        <section className={styles.card}>
          <h2>Risk Heatmap</h2>
          <div className={styles.heatmapGrid}>
            <div className={styles.heatmapCorner} />
            {riskCategories.map(cat => <div key={cat} className={styles.heatmapHeader}>{cat}</div>)}
            {projects.map(proj => (
              <>
                <div key={`label-${proj}`} className={styles.heatmapRowLabel}>{proj}</div>
                {riskCategories.map(cat => {
                  const cell = heatmap.find(c => c.project_name === proj && c.risk_category === cat);
                  const score = cell?.risk_score ?? 0;
                  return (
                    <div
                      key={`${proj}-${cat}`}
                      className={styles.heatmapCell}
                      style={{ background: riskColor(score), opacity: 0.3 + score * 0.7 }}
                      title={`${proj} - ${cat}: ${Math.round(score * 100)}%`}
                    >
                      {Math.round(score * 100)}
                    </div>
                  );
                })}
              </>
            ))}
          </div>
        </section>

        {/* Resource Bottlenecks */}
        <section className={styles.card}>
          <h2>Resource Bottleneck Predictions</h2>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Skill Area</th>
                <th>Severity</th>
                <th>Demand/Capacity</th>
                <th>Period</th>
              </tr>
            </thead>
            <tbody>
              {bottlenecks.map((b, i) => (
                <tr key={i}>
                  <td>{b.skill_area}</td>
                  <td><span className={`${styles.severityBadge} ${styles[`severity-${b.severity}`]}`}>{b.severity}</span></td>
                  <td>{Math.round(b.demand_capacity_ratio * 100)}%</td>
                  <td>{b.bottleneck_start_date} to {b.bottleneck_end_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Scenario Comparison placeholder */}
        <section className={styles.card}>
          <h2>Scenario Comparison</h2>
          <p className={styles.placeholder}>Select scenarios to compare using the Monte Carlo simulator.</p>
        </section>
      </div>
    </div>
  );
}
