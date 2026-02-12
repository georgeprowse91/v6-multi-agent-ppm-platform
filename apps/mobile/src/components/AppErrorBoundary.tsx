import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing } from '../theme';

type AppErrorBoundaryProps = {
  children: React.ReactNode;
  onRecover: () => void;
  onSignOut: () => void;
  onReport: (error: Error, componentStack?: string | null) => void;
};

type AppErrorBoundaryState = {
  error: Error | null;
};

export class AppErrorBoundary extends React.Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  constructor(props: AppErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    this.props.onReport(error, info.componentStack);
  }

  private handleReset = () => {
    this.props.onRecover();
    this.setState({ error: null });
  };

  private handleSignOut = () => {
    this.props.onSignOut();
    this.setState({ error: null });
  };

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <View style={styles.container}>
        <View style={styles.card}>
          <Text style={styles.title}>Something went wrong</Text>
          <Text style={styles.body}>
            We hit an unexpected error. You can retry the app or sign out to start a clean session.
          </Text>
          <Pressable style={styles.primaryButton} onPress={this.handleReset}>
            <Text style={styles.primaryButtonText}>Try again</Text>
          </Pressable>
          <Pressable style={styles.secondaryButton} onPress={this.handleSignOut}>
            <Text style={styles.secondaryButtonText}>Sign out</Text>
          </Pressable>
        </View>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  card: {
    width: '100%',
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.lg,
    gap: spacing.md,
  },
  title: {
    color: colors.text,
    fontSize: 24,
    fontWeight: '700',
  },
  body: {
    color: colors.muted,
    lineHeight: 20,
  },
  primaryButton: {
    backgroundColor: colors.accent,
    borderRadius: radius.sm,
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  primaryButtonText: {
    color: colors.background,
    fontWeight: '700',
  },
  secondaryButton: {
    borderColor: colors.muted,
    borderWidth: 1,
    borderRadius: radius.sm,
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  secondaryButtonText: {
    color: colors.text,
    fontWeight: '600',
  },
});
