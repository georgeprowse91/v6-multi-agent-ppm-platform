import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import * as WebBrowser from 'expo-web-browser';

import { loginUrl } from '../api/client';
import { useAppContext } from '../context/AppContext';
import { colors, radius, spacing } from '../theme';

export const LoginScreen = () => {
  const { refreshSession, loading } = useAppContext();
  const [error, setError] = useState<string | null>(null);
  const [isSigningIn, setIsSigningIn] = useState(false);

  const handleLogin = async () => {
    setIsSigningIn(true);
    setError(null);
    try {
      await WebBrowser.openBrowserAsync(loginUrl());
      await refreshSession();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to start login.');
    } finally {
      setIsSigningIn(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>PPM Mobile</Text>
        <Text style={styles.subtitle}>Sign in to access your workspace.</Text>
        <Pressable style={styles.button} onPress={handleLogin} disabled={isSigningIn}>
          <Text style={styles.buttonText}>Sign in with OIDC</Text>
        </Pressable>
        {isSigningIn && <ActivityIndicator color={colors.accent} />}
        {loading && <Text style={styles.status}>Checking session...</Text>}
        {error && <Text style={styles.error}>{error}</Text>}
        <Text style={styles.helper}>
          The login flow opens the API gateway OIDC screen in your browser. Return here after completing
          authentication to continue.
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    width: '100%',
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.sm,
  },
  subtitle: {
    color: colors.muted,
    marginBottom: spacing.lg,
  },
  button: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.sm,
    borderRadius: radius.sm,
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  buttonText: {
    color: colors.background,
    fontWeight: '600',
  },
  status: {
    color: colors.muted,
    marginTop: spacing.sm,
  },
  error: {
    color: colors.danger,
    marginTop: spacing.sm,
  },
  helper: {
    color: colors.muted,
    marginTop: spacing.md,
    fontSize: 12,
    lineHeight: 18,
  },
});
