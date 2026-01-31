import React, { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { useAppContext } from '../context/AppContext';
import { colors, radius, spacing } from '../theme';

export const TenantSelectionScreen = () => {
  const { session, setTenantId } = useAppContext();
  const [customTenant, setCustomTenant] = useState('');

  const tenantOptions = useMemo(() => {
    if (session.tenant_id) {
      return [session.tenant_id];
    }
    return [] as string[];
  }, [session.tenant_id]);

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>Select tenant</Text>
        <Text style={styles.subtitle}>Choose the tenant context for API requests.</Text>
        {tenantOptions.length > 0 ? (
          tenantOptions.map((tenant) => (
            <Pressable key={tenant} style={styles.option} onPress={() => setTenantId(tenant)}>
              <Text style={styles.optionLabel}>{tenant}</Text>
              <Text style={styles.optionMeta}>OIDC tenant claim</Text>
            </Pressable>
          ))
        ) : (
          <Text style={styles.notice}>No tenant claim found in the session. Enter one below.</Text>
        )}
        <Text style={styles.sectionTitle}>Use a different tenant</Text>
        <TextInput
          style={styles.input}
          placeholder="tenant-id"
          placeholderTextColor={colors.muted}
          value={customTenant}
          onChangeText={setCustomTenant}
        />
        <Pressable
          style={[styles.button, !customTenant && styles.buttonDisabled]}
          onPress={() => customTenant && setTenantId(customTenant)}
          disabled={!customTenant}
        >
          <Text style={styles.buttonText}>Continue</Text>
        </Pressable>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    padding: spacing.lg,
    justifyContent: 'center',
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  subtitle: {
    color: colors.muted,
    marginBottom: spacing.md,
  },
  option: {
    backgroundColor: colors.card,
    padding: spacing.md,
    borderRadius: radius.md,
    marginBottom: spacing.sm,
  },
  optionLabel: {
    color: colors.text,
    fontWeight: '600',
  },
  optionMeta: {
    color: colors.muted,
    fontSize: 12,
    marginTop: spacing.xs,
  },
  notice: {
    color: colors.warning,
    marginBottom: spacing.md,
  },
  sectionTitle: {
    color: colors.text,
    fontWeight: '600',
    marginTop: spacing.md,
    marginBottom: spacing.xs,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.card,
    borderRadius: radius.sm,
    padding: spacing.sm,
    color: colors.text,
    marginBottom: spacing.sm,
  },
  button: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.sm,
    borderRadius: radius.sm,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: colors.background,
    fontWeight: '600',
  },
});
