import * as SecureStore from 'expo-secure-store';

import type { AuthTokens } from '../api/client';
import { authenticateWithBiometrics, isBiometricAvailable } from './biometricAuth';

const SESSION_STORAGE_KEY = 'ppm.mobile.session.tokens';
const BIOMETRIC_ENABLED_KEY = 'ppm.mobile.biometric.enabled';

export const persistSessionTokens = async (tokens: AuthTokens) => {
  await SecureStore.setItemAsync(SESSION_STORAGE_KEY, JSON.stringify(tokens));
};

export const restoreSessionTokens = async (): Promise<AuthTokens | null> => {
  const raw = await SecureStore.getItemAsync(SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as AuthTokens;
    if (!parsed.accessToken) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
};

export const clearSessionTokens = async () => {
  await SecureStore.deleteItemAsync(SESSION_STORAGE_KEY);
};

export const isBiometricLoginEnabled = async (): Promise<boolean> => {
  const available = await isBiometricAvailable();
  if (!available) {
    return false;
  }
  const enabled = await SecureStore.getItemAsync(BIOMETRIC_ENABLED_KEY);
  return enabled === 'true';
};

export const setBiometricLoginEnabled = async (enabled: boolean) => {
  await SecureStore.setItemAsync(BIOMETRIC_ENABLED_KEY, enabled ? 'true' : 'false');
};

export const restoreSessionWithBiometrics = async (): Promise<AuthTokens | null> => {
  const biometricEnabled = await isBiometricLoginEnabled();
  if (!biometricEnabled) {
    return restoreSessionTokens();
  }

  const authenticated = await authenticateWithBiometrics('Authenticate to restore your session');
  if (!authenticated) {
    return null;
  }

  return restoreSessionTokens();
};
