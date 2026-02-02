import React, { useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import {
  fetchPortfolioSummary,
  fetchPortfolios,
  fetchProjectHealth,
  fetchProjectKpis,
  fetchProjects,
} from '../api/client';
import { Card } from '../components/Card';
import { LabelValueRow } from '../components/LabelValueRow';
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

export const DashboardScreen = () => {
  const { tenantId, projectId } = useAppContext();
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [projects, setProjects] = useState<ProjectSnapshot[]>([]);
  const [health, setHealth] = useState<HealthSummary | null>(null);
  const [kpis, setKpis] = useState<Kpi[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryPayload, portfoliosPayload, projectsPayload, healthPayload, kpiPayload] =
        await Promise.all([
          fetchPortfolioSummary(tenantId),
          fetchPortfolios(tenantId),
          fetchProjects(tenantId),
          fetchProjectHealth(projectId, tenantId),
          fetchProjectKpis(projectId, tenantId),
        ]);
      setPortfolioSummary(summaryPayload as PortfolioSummary);
      setPortfolios(normalizePortfolios(portfoliosPayload));
      setProjects(normalizeProjects(projectsPayload));
      setHealth(healthPayload as HealthSummary);
      setKpis(normalizeKpis(kpiPayload));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDashboard();
  }, [tenantId, projectId]);

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
});
