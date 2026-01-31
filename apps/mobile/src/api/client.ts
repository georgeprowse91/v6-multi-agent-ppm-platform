import Constants from 'expo-constants';

type ApiOptions = RequestInit & {
  tenantId?: string | null;
};

const fallbackBaseUrl = 'http://localhost:8000';
const extraBaseUrl =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ||
  process.env.EXPO_PUBLIC_API_BASE_URL;

export const API_BASE_URL = extraBaseUrl || fallbackBaseUrl;

export const apiFetch = async (path: string, options: ApiOptions = {}) => {
  const { tenantId, headers, ...rest } = options;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...rest,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(tenantId ? { 'X-Tenant-ID': tenantId } : {}),
      ...(headers || {}),
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || response.statusText);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }

  return response.text();
};

export const getSession = async () => apiFetch('/session');

export const loginUrl = () => `${API_BASE_URL}/login`;

export const logout = async () => apiFetch('/logout', { method: 'POST' });
