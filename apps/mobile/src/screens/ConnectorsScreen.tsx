import React, { useEffect, useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { apiFetch } from '../api/client';
import { Card } from '../components/Card';
import { useAppContext } from '../context/AppContext';
import { colors, spacing } from '../theme';

type Connector = {
  connector_id?: string;
  name?: string;
  category?: string;
  description?: string;
  enabled?: boolean;
  health?: string;
};

const normalizeConnectors = (payload: any): Connector[] => {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.connectors)) {
    return payload.connectors;
  }
  return [];
};

export const ConnectorsScreen = () => {
  const { tenantId } = useAppContext();
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadConnectors = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await apiFetch('/api/connectors', { tenantId });
      setConnectors(normalizeConnectors(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load connectors.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadConnectors();
  }, [tenantId]);

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Connector Gallery</Text>
      <Text style={styles.subheading}>Enable integrations and monitor connector health.</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      <FlatList
        data={connectors}
        keyExtractor={(item, index) => item.connector_id || item.name || `connector-${index}`}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={loadConnectors} />}
        renderItem={({ item }) => (
          <Card>
            <Text style={styles.cardTitle}>{item.name || 'Connector'}</Text>
            <Text style={styles.cardDescription}>{item.description || 'No description available.'}</Text>
            <Text style={styles.cardMeta}>Category: {item.category || 'General'}</Text>
            <Text style={styles.cardMeta}>Status: {item.enabled ? 'Enabled' : 'Disabled'}</Text>
            {item.health && <Text style={styles.cardMeta}>Health: {item.health}</Text>}
          </Card>
        )}
        ListEmptyComponent={!loading ? <Text style={styles.empty}>No connectors available.</Text> : null}
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
    marginTop: spacing.xs,
    fontSize: 12,
  },
  empty: {
    color: colors.muted,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
});
