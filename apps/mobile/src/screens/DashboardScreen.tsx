import React, { useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { apiFetch } from '../api/client';
import { Card } from '../components/Card';
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

const normalizeKpis = (payload: any): Kpi[] => {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.kpis)) {
    return payload.kpis;
  }
  return [];
};

export const DashboardScreen = () => {
  const { tenantId, projectId } = useAppContext();
  const [health, setHealth] = useState<HealthSummary | null>(null);
  const [kpis, setKpis] = useState<Kpi[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthPayload, kpiPayload] = await Promise.all([
        apiFetch(`/api/dashboard/${projectId}/health`, { tenantId }),
        apiFetch(`/api/dashboard/${projectId}/kpis`, { tenantId }),
      ]);
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
      <Text style={styles.heading}>Dashboard</Text>
      <Text style={styles.subheading}>Project health overview and KPI highlights.</Text>
      {error && <Text style={styles.error}>{error}</Text>}
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
});
