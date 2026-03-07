import React, { useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import {
  fetchHealthForecast,
  fetchPortfolioSummary,
  fetchPortfolios,
  fetchProjectHealth,
  fetchProjectKpis,
  fetchProjects,
} from '../api/client';
import { Card } from '../components/Card';
import { LabelValueRow } from '../components/LabelValueRow';
import { HealthBadgeBar, Sparkline } from '../components/Sparkline';
import { useAppContext } from '../context/AppContext';
import { colors, spacing } from '../theme';

type HealthSummary = {
  status?: string;
  risks?: string[];
  blockers?: string[];
  highlights?: string[];
};

type Kpi = {
  label?: string;
  value?: string | number;
  trend?: string;
};

type PortfolioSummary = {
  name?: string;
  owner?: string;
  total_projects?: number;
  active_projects?: number;
  budget_utilization?: string;
  health?: string;
};

type Portfolio = {
  id?: string;
  name?: string;
  status?: string;
  owner?: string;
  project_count?: number;
};

type ProjectSnapshot = {
  id?: string;
  name?: string;
  stage?: string;
  status?: string;
  risk_level?: string;
};

type HealthPrediction = {
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
};

const normalizeKpis = (payload: any): Kpi[] => {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.kpis)) {
    return payload.kpis;
  }
  return [];
};

const normalizePortfolios = (payload: any): Portfolio[] => {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.portfolios)) {
    return payload.portfolios;
  }
  return [];
};

const normalizeProjects = (payload: any): ProjectSnapshot[] => {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.projects)) {
    return payload.projects;
  }
  return [];
};

const normalizeHealthForecast = (payload: any): HealthPrediction[] => {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.predictions)) {
    return payload.predictions;
  }
  return [];
};

function healthStatusColor(score: number): string {
  if (score >= 0.7) return colors.success;
  if (score >= 0.4) return colors.warning;
  return colors.danger;
}

function trendLabel(trend: string): string {
  switch (trend) {
    case 'improving':
      return '\u2191 Improving';
    case 'declining':
      return '\u2193 Declining';
    case 'rapidly_declining':
      return '\u21CA Rapidly declining';
    default:
      return '\u2192 Stable';
  }
}

function trendColor(trend: string): string {
  switch (trend) {
    case 'improving':
      return colors.success;
    case 'declining':
    case 'rapidly_declining':
      return colors.danger;
    default:
      return colors.muted;
  }
}

export const DashboardScreen = () => {
  const { tenantId, projectId } = useAppContext();
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [projects, setProjects] = useState<ProjectSnapshot[]>([]);
  const [health, setHealth] = useState<HealthSummary | null>(null);
  const [kpis, setKpis] = useState<Kpi[]>([]);
  const [healthForecast, setHealthForecast] = useState<HealthPrediction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryPayload, portfoliosPayload, projectsPayload, healthPayload, kpiPayload, forecastPayload] =
        await Promise.all([
          fetchPortfolioSummary(tenantId),
          fetchPortfolios(tenantId),
          fetchProjects(tenantId),
          fetchProjectHealth(projectId, tenantId),
          fetchProjectKpis(projectId, tenantId),
          fetchHealthForecast('default', tenantId).catch(() => []),
        ]);
      setPortfolioSummary(summaryPayload as PortfolioSummary);
      setPortfolios(normalizePortfolios(portfoliosPayload));
      setProjects(normalizeProjects(projectsPayload));
      setHealth(healthPayload as HealthSummary);
      setKpis(normalizeKpis(kpiPayload));
      setHealthForecast(normalizeHealthForecast(forecastPayload));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDashboard();
  }, [tenantId, projectId]);

  const criticalProjects = healthForecast.filter(p => p.current_health_score < 0.4);
  const atRiskProjects = healthForecast.filter(p => p.current_health_score >= 0.4 && p.current_health_score < 0.7);

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={loadDashboard} />}
    >
      <Text style={styles.heading}>Portfolio & Project Dashboard</Text>
      <Text style={styles.subheading}>Portfolio health, approvals, and KPI snapshots in one view.</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      <Card>
        <Text style={styles.cardTitle}>Portfolio Snapshot</Text>
        <Text style={styles.cardSubtitle}>{portfolioSummary?.name || 'Primary Portfolio'}</Text>
        <LabelValueRow label="Owner" value={portfolioSummary?.owner || 'Portfolio office'} />
        <LabelValueRow
          label="Total projects"
          value={portfolioSummary?.total_projects ?? portfolios.length}
        />
        <LabelValueRow
          label="Active projects"
          value={portfolioSummary?.active_projects ?? projects.length}
          accent
        />
        <LabelValueRow
          label="Budget utilization"
          value={portfolioSummary?.budget_utilization || 'On track'}
        />
        <LabelValueRow label="Health" value={portfolioSummary?.health || 'Steady'} accent />
      </Card>

      {/* Predictive Health Scoring Section */}
      {healthForecast.length > 0 && (
        <>
          <View style={styles.sectionHeader}>
            <Text style={styles.cardTitle}>Predictive Health Scores</Text>
          </View>

          {/* Summary badges */}
          <View style={styles.healthSummaryRow}>
            <View style={styles.healthSummaryBadge}>
              <Text style={styles.healthSummaryCount}>{healthForecast.length}</Text>
              <Text style={styles.healthSummaryLabel}>Tracked</Text>
            </View>
            {criticalProjects.length > 0 && (
              <View style={[styles.healthSummaryBadge, styles.healthCriticalBg]}>
                <Text style={[styles.healthSummaryCount, styles.healthCriticalText]}>
                  {criticalProjects.length}
                </Text>
                <Text style={styles.healthSummaryLabel}>Critical</Text>
              </View>
            )}
            {atRiskProjects.length > 0 && (
              <View style={[styles.healthSummaryBadge, styles.healthWarningBg]}>
                <Text style={[styles.healthSummaryCount, styles.healthWarningText]}>
                  {atRiskProjects.length}
                </Text>
                <Text style={styles.healthSummaryLabel}>At Risk</Text>
              </View>
            )}
          </View>

          {/* Per-project health predictions */}
          {healthForecast.map((prediction) => (
            <Card key={prediction.project_id}>
              <View style={styles.healthProjectHeader}>
                <Text style={styles.healthProjectName}>
                  {prediction.project_name || prediction.project_id}
                </Text>
                <View
                  style={[
                    styles.healthBadge,
                    { backgroundColor: healthStatusColor(prediction.current_health_score) },
                  ]}
                >
                  <Text style={styles.healthBadgeText}>
                    {Math.round(prediction.current_health_score * 100)}
                  </Text>
                </View>
              </View>

              <Text style={[styles.trendText, { color: trendColor(prediction.trend) }]}>
                {trendLabel(prediction.trend)}
              </Text>

              <View style={styles.forecastRow}>
                <View style={styles.forecastItem}>
                  <Text style={styles.forecastLabel}>30d</Text>
                  <Text
                    style={[
                      styles.forecastValue,
                      { color: healthStatusColor(prediction.predicted_health_30d) },
                    ]}
                  >
                    {Math.round(prediction.predicted_health_30d * 100)}%
                  </Text>
                </View>
                <View style={styles.forecastItem}>
                  <Text style={styles.forecastLabel}>60d</Text>
                  <Text
                    style={[
                      styles.forecastValue,
                      { color: healthStatusColor(prediction.predicted_health_60d) },
                    ]}
                  >
                    {Math.round(prediction.predicted_health_60d * 100)}%
                  </Text>
                </View>
                <View style={styles.forecastItem}>
                  <Text style={styles.forecastLabel}>90d</Text>
                  <Text
                    style={[
                      styles.forecastValue,
                      { color: healthStatusColor(prediction.predicted_health_90d) },
                    ]}
                  >
                    {Math.round(prediction.predicted_health_90d * 100)}%
                  </Text>
                </View>
              </View>

              {/* Signal breakdown with sparklines */}
              <View style={styles.signalGrid}>
                <View style={styles.signalItem}>
                  <Text style={styles.signalLabel}>Risk</Text>
                  <HealthBadgeBar score={1 - prediction.risk_signal} width={80} height={6} />
                  <Sparkline
                    data={[
                      1 - prediction.risk_signal * 1.2,
                      1 - prediction.risk_signal * 1.1,
                      1 - prediction.risk_signal,
                    ]}
                    width={60}
                    height={20}
                    color={healthStatusColor(1 - prediction.risk_signal)}
                  />
                </View>
                <View style={styles.signalItem}>
                  <Text style={styles.signalLabel}>Schedule</Text>
                  <HealthBadgeBar score={prediction.schedule_signal} width={80} height={6} />
                  <Sparkline
                    data={[
                      prediction.schedule_signal * 0.9,
                      prediction.schedule_signal * 0.95,
                      prediction.schedule_signal,
                    ]}
                    width={60}
                    height={20}
                    color={healthStatusColor(prediction.schedule_signal)}
                  />
                </View>
                <View style={styles.signalItem}>
                  <Text style={styles.signalLabel}>Budget</Text>
                  <HealthBadgeBar score={prediction.budget_signal} width={80} height={6} />
                  <Sparkline
                    data={[
                      prediction.budget_signal * 0.85,
                      prediction.budget_signal * 0.92,
                      prediction.budget_signal,
                    ]}
                    width={60}
                    height={20}
                    color={healthStatusColor(prediction.budget_signal)}
                  />
                </View>
                <View style={styles.signalItem}>
                  <Text style={styles.signalLabel}>Resource</Text>
                  <HealthBadgeBar score={prediction.resource_signal} width={80} height={6} />
                  <Sparkline
                    data={[
                      prediction.resource_signal * 0.88,
                      prediction.resource_signal * 0.94,
                      prediction.resource_signal,
                    ]}
                    width={60}
                    height={20}
                    color={healthStatusColor(prediction.resource_signal)}
                  />
                </View>
              </View>

              {/* Health trend sparkline */}
              <View style={styles.sparklineRow}>
                <Text style={styles.signalLabel}>Health trend</Text>
                <Sparkline
                  data={[
                    prediction.predicted_health_90d,
                    prediction.predicted_health_60d,
                    prediction.predicted_health_30d,
                    prediction.current_health_score,
                  ]}
                  width={120}
                  height={28}
                  color={healthStatusColor(prediction.current_health_score)}
                  strokeWidth={2}
                />
              </View>
            </Card>
          ))}
        </>
      )}

      <View style={styles.sectionHeader}>
        <Text style={styles.cardTitle}>Portfolios</Text>
      </View>
      {portfolios.length === 0 && !loading ? (
        <Text style={styles.empty}>No portfolio records available.</Text>
      ) : null}
      {portfolios.map((portfolio, index) => (
        <Card key={portfolio.id || portfolio.name || `portfolio-${index}`}>
          <Text style={styles.cardTitle}>{portfolio.name || 'Portfolio'}</Text>
          <Text style={styles.cardDescription}>Owner: {portfolio.owner || 'PMO team'}</Text>
          <LabelValueRow label="Status" value={portfolio.status || 'Active'} accent />
          <LabelValueRow
            label="Projects"
            value={portfolio.project_count ?? 'Portfolio detail pending'}
          />
        </Card>
      ))}
      <View style={styles.sectionHeader}>
        <Text style={styles.cardTitle}>Project Health</Text>
      </View>
      <Card>
        <Text style={styles.cardTitle}>Health Status</Text>
        <Text style={styles.status}>{health?.status || 'Unknown'}</Text>
        <Text style={styles.cardMeta}>Risks</Text>
        {(health?.risks || ['No active risks reported']).map((risk, index) => (
          <Text key={`risk-${index}`} style={styles.listItem}>
            • {risk}
          </Text>
        ))}
        <Text style={styles.cardMeta}>Blockers</Text>
        {(health?.blockers || ['No blockers reported']).map((blocker, index) => (
          <Text key={`blocker-${index}`} style={styles.listItem}>
            • {blocker}
          </Text>
        ))}
      </Card>
      <Card>
        <Text style={styles.cardTitle}>Highlights</Text>
        {(health?.highlights || ['Key wins will appear here once the project is active.']).map(
          (highlight, index) => (
            <Text key={`highlight-${index}`} style={styles.listItem}>
              • {highlight}
            </Text>
          )
        )}
      </Card>
      <View style={styles.sectionHeader}>
        <Text style={styles.cardTitle}>KPI Snapshot</Text>
      </View>
      {kpis.length === 0 && !loading ? <Text style={styles.empty}>No KPIs available.</Text> : null}
      {kpis.map((kpi, index) => (
        <Card key={`kpi-${index}`}>
          <Text style={styles.kpiLabel}>{kpi.label || 'KPI'}</Text>
          <Text style={styles.kpiValue}>{kpi.value ?? '—'}</Text>
          {kpi.trend ? <Text style={styles.cardMeta}>Trend: {kpi.trend}</Text> : null}
        </Card>
      ))}
      <View style={styles.sectionHeader}>
        <Text style={styles.cardTitle}>Projects</Text>
      </View>
      {projects.length === 0 && !loading ? (
        <Text style={styles.empty}>No project snapshots available.</Text>
      ) : null}
      {projects.map((project, index) => (
        <Card key={project.id || project.name || `project-${index}`}>
          <Text style={styles.cardTitle}>{project.name || 'Project'}</Text>
          <Text style={styles.cardDescription}>Stage: {project.stage || 'Planning'}</Text>
          <LabelValueRow label="Status" value={project.status || 'In progress'} accent />
          <LabelValueRow label="Risk" value={project.risk_level || 'Low'} />
        </Card>
      ))}
      {loading && portfolios.length === 0 && projects.length === 0 ? (
        <Text style={styles.loading}>Refreshing dashboard data...</Text>
      ) : null}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    padding: spacing.lg,
  },
  heading: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.text,
  },
  subheading: {
    color: colors.muted,
    marginBottom: spacing.md,
  },
  error: {
    color: colors.danger,
    marginBottom: spacing.md,
  },
  cardTitle: {
    color: colors.text,
    fontWeight: '600',
    fontSize: 16,
    marginBottom: spacing.sm,
  },
  cardSubtitle: {
    color: colors.muted,
    marginBottom: spacing.sm,
  },
  cardDescription: {
    color: colors.muted,
    marginBottom: spacing.xs,
  },
  status: {
    color: colors.success,
    fontWeight: '700',
    fontSize: 18,
    marginBottom: spacing.sm,
  },
  cardMeta: {
    color: colors.muted,
    marginTop: spacing.sm,
    fontSize: 12,
  },
  listItem: {
    color: colors.text,
    marginTop: spacing.xs,
  },
  sectionHeader: {
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  kpiLabel: {
    color: colors.muted,
    fontSize: 12,
  },
  kpiValue: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '700',
    marginTop: spacing.xs,
  },
  empty: {
    color: colors.muted,
    marginBottom: spacing.md,
  },
  loading: {
    color: colors.muted,
    marginBottom: spacing.lg,
  },
  // Predictive Health Scoring styles
  healthSummaryRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  healthSummaryBadge: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.xs,
    borderRadius: 8,
    backgroundColor: colors.surface,
  },
  healthCriticalBg: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
  },
  healthWarningBg: {
    backgroundColor: 'rgba(234, 179, 8, 0.15)',
  },
  healthSummaryCount: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.text,
  },
  healthCriticalText: {
    color: colors.danger,
  },
  healthWarningText: {
    color: colors.warning,
  },
  healthSummaryLabel: {
    fontSize: 10,
    color: colors.muted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  healthProjectHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  healthProjectName: {
    color: colors.text,
    fontWeight: '600',
    fontSize: 15,
    flex: 1,
  },
  healthBadge: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 12,
    minWidth: 36,
    alignItems: 'center',
  },
  healthBadgeText: {
    color: '#ffffff',
    fontWeight: '700',
    fontSize: 13,
  },
  trendText: {
    fontSize: 12,
    marginBottom: spacing.sm,
  },
  forecastRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: spacing.sm,
    paddingVertical: spacing.xs,
  },
  forecastItem: {
    alignItems: 'center',
  },
  forecastLabel: {
    fontSize: 11,
    color: colors.muted,
    marginBottom: 2,
  },
  forecastValue: {
    fontSize: 16,
    fontWeight: '700',
  },
  signalGrid: {
    gap: spacing.xs,
  },
  signalItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  signalLabel: {
    fontSize: 11,
    color: colors.muted,
    width: 60,
  },
  signalBarBg: {
    flex: 1,
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.1)',
    overflow: 'hidden',
  },
  signalBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  sparklineRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.05)',
  },
});
