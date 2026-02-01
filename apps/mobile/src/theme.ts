import { tokens } from '../../../design-system/tokens/tokens';

export const colors = {
  background: tokens.color.darkMode.surfacePage,
  surface: tokens.color.darkMode.surfaceCard,
  card: tokens.color.darkMode.surfaceCard,
  text: tokens.color.darkMode.textPrimary,
  muted: tokens.color.darkMode.textSecondary,
  accent: tokens.color.brand.orange500,
  success: tokens.color.state.success.fg,
  warning: tokens.color.state.warning.fg,
  danger: tokens.color.state.error.fg,
};

export const spacing = {
  xs: tokens.spacingPx.sm,
  sm: tokens.spacingPx.md,
  md: tokens.spacingPx.lg,
  lg: tokens.spacingPx.xl,
  xl: tokens.spacingPx['2xl'],
};

export const radius = {
  sm: tokens.radiusPx.md,
  md: tokens.radiusPx.lg,
  lg: tokens.radiusPx.pill,
};
