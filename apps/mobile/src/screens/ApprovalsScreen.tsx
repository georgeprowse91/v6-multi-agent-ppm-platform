import React, { useEffect, useMemo, useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { fetchApprovals, submitApprovalAction } from '../api/client';
import { Card } from '../components/Card';
import { LabelValueRow } from '../components/LabelValueRow';
import { useAppContext } from '../context/AppContext';
import { colors, radius, spacing } from '../theme';

type Approval = {
  approval_id?: string;
  title?: string;
  status?: string;
  requested_by?: string;
  due_date?: string;
  workflow?: string;
  summary?: string;
};

const normalizeApprovals = (payload: any): Approval[] => {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.approvals)) {
    return payload.approvals;
  }
  return [];
};

export const ApprovalsScreen = () => {
  const { tenantId } = useAppContext();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadApprovals = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchApprovals(tenantId, 'pending');
      setApprovals(normalizeApprovals(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load approvals.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadApprovals();
  }, [tenantId]);

  const handleAction = async (approvalId: string, action: 'approve' | 'reject') => {
    try {
      await submitApprovalAction(approvalId, action, tenantId);
      await loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Unable to ${action} approval.`);
    }
  };

  const pendingCount = useMemo(
    () => approvals.filter((approval) => approval.status?.toLowerCase() !== 'approved').length,
    [approvals]
  );

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Approval Inbox</Text>
      <Text style={styles.subheading}>Review pending workflow approvals and stage-gate requests.</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      <Card>
        <Text style={styles.cardTitle}>Pending approvals</Text>
        <Text style={styles.pendingCount}>{pendingCount} awaiting action</Text>
        <Text style={styles.cardMeta}>Pull to refresh for the latest approvals.</Text>
      </Card>
      <FlatList
        data={approvals}
        keyExtractor={(item, index) => item.approval_id || item.title || `approval-${index}`}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={loadApprovals} />}
        renderItem={({ item }) => (
          <Card>
            <Text style={styles.cardTitle}>{item.title || 'Approval request'}</Text>
            <Text style={styles.cardDescription}>{item.summary || 'Awaiting your review.'}</Text>
            <LabelValueRow label="Workflow" value={item.workflow || 'Stage gate'} accent />
            <LabelValueRow label="Requested by" value={item.requested_by || 'Automated agent'} />
            <LabelValueRow label="Due" value={item.due_date || 'No deadline'} />
            <LabelValueRow label="Status" value={item.status || 'Pending'} accent />
            {item.approval_id ? (
              <View style={styles.actionsRow}>
                <Pressable
                  style={[styles.actionButton, styles.approveButton]}
                  onPress={() => handleAction(item.approval_id as string, 'approve')}
                >
                  <Text style={styles.actionText}>Approve</Text>
                </Pressable>
                <Pressable
                  style={[styles.actionButton, styles.rejectButton]}
                  onPress={() => handleAction(item.approval_id as string, 'reject')}
                >
                  <Text style={styles.actionText}>Reject</Text>
                </Pressable>
              </View>
            ) : null}
          </Card>
        )}
        ListEmptyComponent={
          !loading ? <Text style={styles.empty}>No approvals require your attention.</Text> : null
        }
      />
    </View>
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
  },
  cardDescription: {
    color: colors.muted,
    marginTop: spacing.xs,
  },
  cardMeta: {
    color: colors.muted,
    marginTop: spacing.sm,
    fontSize: 12,
  },
  pendingCount: {
    color: colors.accent,
    fontSize: 18,
    fontWeight: '700',
    marginTop: spacing.xs,
  },
  actionsRow: {
    marginTop: spacing.sm,
    flexDirection: 'row',
    gap: spacing.sm,
  },
  actionButton: {
    flex: 1,
    paddingVertical: spacing.xs,
    borderRadius: radius.sm,
    alignItems: 'center',
  },
  approveButton: {
    backgroundColor: colors.accent,
  },
  rejectButton: {
    backgroundColor: colors.danger,
  },
  actionText: {
    color: colors.text,
    fontWeight: '600',
  },
  empty: {
    color: colors.muted,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
});
