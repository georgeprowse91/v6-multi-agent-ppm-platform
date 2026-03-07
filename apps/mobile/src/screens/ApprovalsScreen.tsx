import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Animated,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Swipeable } from 'react-native-gesture-handler';

import { fetchApprovals, submitApprovalAction } from '../api/client';
import { Card } from '../components/Card';
import { LabelValueRow } from '../components/LabelValueRow';
import { useAppContext } from '../context/AppContext';
import { enqueueApprovalAction, replayApprovalQueue } from '../services/approvalQueue';
import { authenticateForApproval } from '../services/biometricAuth';
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

const SWIPE_THRESHOLD = 80;

const renderRightActions = (
  _progress: Animated.AnimatedInterpolation<number>,
  dragX: Animated.AnimatedInterpolation<number>
) => {
  const scale = dragX.interpolate({
    inputRange: [-SWIPE_THRESHOLD, 0],
    outputRange: [1, 0.5],
    extrapolate: 'clamp',
  });

  return (
    <View style={styles.swipeActionRight}>
      <Animated.Text style={[styles.swipeActionText, { transform: [{ scale }] }]}>
        Reject
      </Animated.Text>
    </View>
  );
};

const renderLeftActions = (
  _progress: Animated.AnimatedInterpolation<number>,
  dragX: Animated.AnimatedInterpolation<number>
) => {
  const scale = dragX.interpolate({
    inputRange: [0, SWIPE_THRESHOLD],
    outputRange: [0.5, 1],
    extrapolate: 'clamp',
  });

  return (
    <View style={styles.swipeActionLeft}>
      <Animated.Text style={[styles.swipeActionText, { transform: [{ scale }] }]}>
        Approve
      </Animated.Text>
    </View>
  );
};

type ApprovalCardProps = {
  item: Approval;
  onAction: (approvalId: string, action: 'approve' | 'reject') => void;
};

const ApprovalCard: React.FC<ApprovalCardProps> = ({ item, onAction }) => {
  const swipeableRef = useRef<Swipeable>(null);

  const handleSwipeLeft = useCallback(() => {
    if (item.approval_id) {
      onAction(item.approval_id, 'reject');
    }
    swipeableRef.current?.close();
  }, [item.approval_id, onAction]);

  const handleSwipeRight = useCallback(() => {
    if (item.approval_id) {
      onAction(item.approval_id, 'approve');
    }
    swipeableRef.current?.close();
  }, [item.approval_id, onAction]);

  return (
    <Swipeable
      ref={swipeableRef}
      renderRightActions={item.approval_id ? renderRightActions : undefined}
      renderLeftActions={item.approval_id ? renderLeftActions : undefined}
      onSwipeableOpen={(direction) => {
        if (direction === 'right') {
          handleSwipeLeft();
        } else {
          handleSwipeRight();
        }
      }}
      overshootRight={false}
      overshootLeft={false}
    >
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
              onPress={() => onAction(item.approval_id as string, 'approve')}
            >
              <Text style={styles.actionText}>Approve</Text>
            </Pressable>
            <Pressable
              style={[styles.actionButton, styles.rejectButton]}
              onPress={() => onAction(item.approval_id as string, 'reject')}
            >
              <Text style={styles.actionText}>Reject</Text>
            </Pressable>
          </View>
        ) : null}
        <Text style={styles.swipeHint}>Swipe right to approve, left to reject</Text>
      </Card>
    </Swipeable>
  );
};

export const ApprovalsScreen = () => {
  const { tenantId } = useAppContext();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queueCount, setQueueCount] = useState(0);

  const loadApprovals = async () => {
    setLoading(true);
    setError(null);
    try {
      const replayResult = await replayApprovalQueue();
      setQueueCount(replayResult.remaining);

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

  const handleAction = useCallback(
    async (approvalId: string, action: 'approve' | 'reject') => {
      const approvalItem = approvals.find((a) => a.approval_id === approvalId);

      const authenticated = await authenticateForApproval(approvalItem?.title);
      if (!authenticated) {
        return;
      }

      try {
        await submitApprovalAction(approvalId, action, tenantId);
        await loadApprovals();
      } catch (err) {
        const queued = await enqueueApprovalAction(approvalId, action, tenantId);
        setQueueCount((prev) => prev + 1);
        Alert.alert(
          'Queued Offline',
          `Your ${action} action has been saved and will be submitted when connectivity is restored.`,
          [{ text: 'OK' }]
        );
      }
    },
    [approvals, tenantId]
  );

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
        {queueCount > 0 && (
          <Text style={styles.queueBadge}>
            {queueCount} queued offline
          </Text>
        )}
        <Text style={styles.cardMeta}>Pull to refresh for the latest approvals.</Text>
      </Card>
      <FlatList
        data={approvals}
        keyExtractor={(item, index) => item.approval_id || item.title || `approval-${index}`}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={loadApprovals} />}
        renderItem={({ item }) => <ApprovalCard item={item} onAction={handleAction} />}
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
  queueBadge: {
    color: colors.warning,
    fontSize: 13,
    fontWeight: '600',
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
  swipeHint: {
    color: colors.muted,
    fontSize: 10,
    marginTop: spacing.sm,
    textAlign: 'center',
    opacity: 0.6,
  },
  swipeActionLeft: {
    backgroundColor: colors.accent,
    justifyContent: 'center',
    alignItems: 'flex-start',
    paddingHorizontal: spacing.lg,
    borderRadius: radius.sm,
    marginVertical: spacing.xs,
    flex: 1,
  },
  swipeActionRight: {
    backgroundColor: colors.danger,
    justifyContent: 'center',
    alignItems: 'flex-end',
    paddingHorizontal: spacing.lg,
    borderRadius: radius.sm,
    marginVertical: spacing.xs,
    flex: 1,
  },
  swipeActionText: {
    color: colors.text,
    fontWeight: '700',
    fontSize: 14,
  },
});
