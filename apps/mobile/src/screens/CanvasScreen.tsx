import React, { useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { fetchCanvasSnapshot } from '../api/client';
import { Card } from '../components/Card';
import { LabelValueRow } from '../components/LabelValueRow';
import { useAppContext } from '../context/AppContext';
import { colors, spacing } from '../theme';

type CanvasSnapshot = {
  stage?: string;
  phase?: string;
  owner?: string;
  updated_at?: string;
  focus_areas?: string[];
  workstreams?: string[];
  risks?: string[];
  approvals_needed?: string[];
  next_milestones?: string[];
};

const normalizeList = (value: any, fallbackKey?: string): string[] => {
  if (Array.isArray(value)) {
    return value.filter(Boolean);
  }
  if (fallbackKey && value && Array.isArray(value[fallbackKey])) {
    return value[fallbackKey].filter(Boolean);
  }
  return [];
};

const normalizeSnapshot = (payload: any): CanvasSnapshot => {
  if (payload && payload.canvas) {
    return payload.canvas as CanvasSnapshot;
  }
  if (payload && payload.snapshot) {
    return payload.snapshot as CanvasSnapshot;
  }
  return payload as CanvasSnapshot;
};

export const CanvasScreen = () => {
  const { tenantId, projectId } = useAppContext();
  const [snapshot, setSnapshot] = useState<CanvasSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCanvas = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchCanvasSnapshot(projectId, tenantId);
      setSnapshot(normalizeSnapshot(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load canvas.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadCanvas();
  }, [tenantId, projectId]);

  const focusAreas = normalizeList(snapshot?.focus_areas);
  const workstreams = normalizeList(snapshot?.workstreams);
  const risks = normalizeList(snapshot?.risks);
  const approvals = normalizeList(snapshot?.approvals_needed);
  const milestones = normalizeList(snapshot?.next_milestones);

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={loadCanvas} />}
    >
      <Text style={styles.heading}>Interactive Canvas</Text>
      <Text style={styles.subheading}>Track delivery focus areas, milestones, and gate readiness.</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      <Card>
        <Text style={styles.cardTitle}>Current Stage</Text>
        <LabelValueRow label="Phase" value={snapshot?.phase || 'Discovery'} accent />
        <LabelValueRow label="Stage" value={snapshot?.stage || 'Intake'} />
        <LabelValueRow label="Owner" value={snapshot?.owner || 'Project lead'} />
        <LabelValueRow label="Last updated" value={snapshot?.updated_at || 'Just now'} />
      </Card>
      <Card>
        <Text style={styles.cardTitle}>Next Milestones</Text>
        {milestones.length === 0 ? (
          <Text style={styles.empty}>Milestones will appear as the canvas updates.</Text>
        ) : (
          milestones.map((milestone, index) => (
            <Text key={`milestone-${index}`} style={styles.listItem}>
              • {milestone}
            </Text>
          ))
        )}
      </Card>
      <Card>
        <Text style={styles.cardTitle}>Focus Areas</Text>
        {focusAreas.length === 0 ? (
          <Text style={styles.empty}>No focus areas configured yet.</Text>
        ) : (
          focusAreas.map((area, index) => (
            <Text key={`focus-${index}`} style={styles.listItem}>
              • {area}
            </Text>
          ))
        )}
      </Card>
      <Card>
        <Text style={styles.cardTitle}>Active Workstreams</Text>
        {workstreams.length === 0 ? (
          <Text style={styles.empty}>Workstreams are synced once initiatives are active.</Text>
        ) : (
          workstreams.map((stream, index) => (
            <Text key={`workstream-${index}`} style={styles.listItem}>
              • {stream}
            </Text>
          ))
        )}
      </Card>
      <Card>
        <Text style={styles.cardTitle}>Risks & Blockers</Text>
        {risks.length === 0 ? (
          <Text style={styles.empty}>No critical risks at the moment.</Text>
        ) : (
          risks.map((risk, index) => (
            <Text key={`risk-${index}`} style={styles.listItem}>
              • {risk}
            </Text>
          ))
        )}
      </Card>
      <Card>
        <Text style={styles.cardTitle}>Approvals Needed</Text>
        {approvals.length === 0 ? (
          <Text style={styles.empty}>Approvals are up to date for this stage.</Text>
        ) : (
          approvals.map((approval, index) => (
            <Text key={`approval-${index}`} style={styles.listItem}>
              • {approval}
            </Text>
          ))
        )}
      </Card>
      {loading && !snapshot ? (
        <Text style={styles.loading}>Refreshing canvas data...</Text>
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
  listItem: {
    color: colors.text,
    marginTop: spacing.xs,
  },
  empty: {
    color: colors.muted,
    marginTop: spacing.xs,
  },
  loading: {
    color: colors.muted,
    marginBottom: spacing.lg,
  },
});
