import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing } from '../theme';

type LabelValueRowProps = {
  label: string;
  value: string | number | null | undefined;
  accent?: boolean;
};

export const LabelValueRow = ({ label, value, accent = false }: LabelValueRowProps) => {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, accent && styles.valueAccent]}>{value ?? '—'}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.xs,
  },
  label: {
    color: colors.muted,
    fontSize: 12,
  },
  value: {
    color: colors.text,
    fontWeight: '600',
  },
  valueAccent: {
    color: colors.accent,
  },
});
