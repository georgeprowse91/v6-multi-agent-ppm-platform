import React, { useCallback, useEffect, useState } from 'react';
import {
  AppState,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { Card } from '../components/Card';
import { LabelValueRow } from '../components/LabelValueRow';
import { useAppContext } from '../context/AppContext';
import {
  enqueueStatusUpdate,
  loadStatusQueue,
  replayStatusQueue,
  type QueuedStatusUpdate,
} from '../services/statusQueue';
import { colors, radius, spacing } from '../theme';

export const StatusUpdatesScreen = () => {
  const { tenantId, projectId } = useAppContext();
  const [status, setStatus] = useState('On Track');
  const [summary, setSummary] = useState('');
  const [queue, setQueue] = useState<QueuedStatusUpdate[]>([]);
  const [replayMessage, setReplayMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refreshQueue = useCallback(async () => {
    const queued = await loadStatusQueue();
    setQueue(queued);
  }, []);

  const runReplay = useCallback(async () => {
    const result = await replayStatusQueue();
    setReplayMessage(`Synced ${result.delivered}; ${result.remaining} remaining.`);
    await refreshQueue();
  }, [refreshQueue]);

  useEffect(() => {
    void refreshQueue();

    const appStateSubscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        void runReplay();
      }
    });

    const timer = setInterval(() => {
      void runReplay();
    }, 20000);

    return () => {
      appStateSubscription.remove();
      clearInterval(timer);
    };
  }, [refreshQueue, runReplay]);

  const queueStatusUpdate = async () => {
    if (!summary.trim()) {
      setReplayMessage('Summary is required.');
      return;
    }

    setLoading(true);
    await enqueueStatusUpdate(
      {
        project_id: projectId,
        status,
        summary,
        updated_at: new Date().toISOString(),
      },
      tenantId
    );
    setSummary('');
    await refreshQueue();
    setReplayMessage('Status update queued for delivery.');
    setLoading(false);
  };

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={refreshQueue} />}
    >
      <Text style={styles.heading}>Status Submit Queue</Text>
      <Text style={styles.subheading}>Capture updates offline and replay automatically on reconnect.</Text>
      <Card>
        <Text style={styles.cardTitle}>Submit project status</Text>
        <TextInput value={status} onChangeText={setStatus} style={styles.input} placeholder="Status" />
        <TextInput
          value={summary}
          onChangeText={setSummary}
          style={[styles.input, styles.multiline]}
          placeholder="Summary"
          multiline
        />
        <Pressable style={styles.button} onPress={queueStatusUpdate}>
          <Text style={styles.buttonText}>Queue status update</Text>
        </Pressable>
        <Pressable style={[styles.button, styles.secondary]} onPress={runReplay}>
          <Text style={styles.buttonText}>Retry queued updates now</Text>
        </Pressable>
        {replayMessage ? <Text style={styles.meta}>{replayMessage}</Text> : null}
      </Card>

      <View style={styles.sectionHeader}>
        <Text style={styles.cardTitle}>Queued updates ({queue.length})</Text>
      </View>
      {queue.map((item) => (
        <Card key={item.id}>
          <Text style={styles.cardTitle}>{item.status}</Text>
          <Text style={styles.meta}>{item.summary}</Text>
          <LabelValueRow label="Project" value={item.project_id} />
          <LabelValueRow label="Created" value={item.createdAt} />
          <LabelValueRow label="Retries" value={item.retries} accent />
        </Card>
      ))}
      {queue.length === 0 ? <Text style={styles.meta}>No queued status updates.</Text> : null}
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
  cardTitle: {
    color: colors.text,
    fontWeight: '600',
    fontSize: 16,
    marginBottom: spacing.sm,
  },
  input: {
    backgroundColor: colors.surface,
    color: colors.text,
    borderColor: colors.card,
    borderWidth: 1,
    borderRadius: radius.sm,
    padding: spacing.sm,
    marginBottom: spacing.sm,
  },
  multiline: {
    minHeight: 80,
  },
  button: {
    backgroundColor: colors.accent,
    borderRadius: radius.sm,
    paddingVertical: spacing.sm,
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  secondary: {
    backgroundColor: colors.card,
  },
  buttonText: {
    color: colors.text,
    fontWeight: '600',
  },
  meta: {
    color: colors.muted,
    marginTop: spacing.xs,
  },
  sectionHeader: {
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
});
