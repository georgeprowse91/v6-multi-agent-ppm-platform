import * as SecureStore from 'expo-secure-store';

import type { AuthTokens } from '../api/client';

const SESSION_STORAGE_KEY = 'ppm.mobile.session.tokens';

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
