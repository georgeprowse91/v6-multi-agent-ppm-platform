import React, { useEffect, useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { apiFetch } from '../api/client';
import { Card } from '../components/Card';
import { useAppContext } from '../context/AppContext';
import { colors, spacing } from '../theme';

type Methodology = {
  id?: string;
  name?: string;
  description?: string;
  stages?: { id: string; name: string }[];
};

const normalizeMethodologies = (payload: any): Methodology[] => {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.items)) {
    return payload.items;
  }
  if (payload && Array.isArray(payload.methodologies)) {
    return payload.methodologies;
  }
  return [];
};

export const MethodologiesScreen = () => {
  const { tenantId } = useAppContext();
  const [data, setData] = useState<Methodology[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMethodologies = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await apiFetch('/api/methodologies', { tenantId });
      setData(normalizeMethodologies(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load methodologies.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadMethodologies();
  }, [tenantId]);

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Methodologies</Text>
      <Text style={styles.subheading}>Browse available delivery frameworks and their stages.</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      <FlatList
        data={data}
        keyExtractor={(item, index) => item.id || item.name || `methodology-${index}`}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={loadMethodologies} />}
        renderItem={({ item }) => (
          <Card>
            <Text style={styles.cardTitle}>{item.name || 'Untitled methodology'}</Text>
            <Text style={styles.cardDescription}>{item.description || 'No description provided.'}</Text>
            <Text style={styles.cardMeta}>
              {item.stages?.length ? `${item.stages.length} stages` : 'Stage details available in the canvas'}
            </Text>
          </Card>
        )}
        ListEmptyComponent={!loading ? <Text style={styles.empty}>No methodologies found.</Text> : null}
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
    color: colors.accent,
    marginTop: spacing.sm,
    fontSize: 12,
  },
  empty: {
    color: colors.muted,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
});
