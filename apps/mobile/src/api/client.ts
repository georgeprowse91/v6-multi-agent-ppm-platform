import Constants from 'expo-constants';

export type AuthTokens = {
  accessToken: string;
  refreshToken?: string;
};

type ApiOptions = RequestInit & {
  tenantId?: string | null;
};

export type ApprovalAction = 'approve' | 'reject';

export type StatusUpdatePayload = {
  project_id: string;
  status: string;
  summary: string;
  updated_at?: string;
};

const fallbackBaseUrl = 'http://localhost:8000';
const extraBaseUrl =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ||
  process.env.EXPO_PUBLIC_API_BASE_URL;

export const API_BASE_URL = extraBaseUrl || fallbackBaseUrl;

let authTokens: AuthTokens | null = null;

export const setAuthTokens = (tokens: AuthTokens | null) => {
  authTokens = tokens;
};

export const getAuthTokens = () => authTokens;

export const apiFetch = async (path: string, options: ApiOptions = {}) => {
  const { tenantId, headers, ...rest } = options;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...rest,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(authTokens?.accessToken ? { Authorization: `Bearer ${authTokens.accessToken}` } : {}),
      ...(tenantId ? { 'X-Tenant-ID': tenantId } : {}),
      ...(headers || {}),
    },
  });

  if (response.status === 401) {
    const unauthorizedError = new Error('Unauthorized');
    unauthorizedError.name = 'UnauthorizedError';
    throw unauthorizedError;
  }

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

export const fetchPortfolioSummary = async (tenantId?: string | null) =>
  apiFetch('/api/portfolios/summary', { tenantId });

export const fetchPortfolios = async (tenantId?: string | null) => apiFetch('/api/portfolios', { tenantId });

export const fetchProjects = async (tenantId?: string | null) => apiFetch('/api/projects', { tenantId });

export const fetchApprovals = async (tenantId?: string | null, status?: string) => {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  return apiFetch(`/api/workflows/approvals${query}`, { tenantId });
};

export const submitApprovalAction = async (
  approvalId: string,
  action: ApprovalAction,
  tenantId?: string | null
) =>
  apiFetch(`/api/workflows/approvals/${encodeURIComponent(approvalId)}/actions`, {
    method: 'POST',
    tenantId,
    body: JSON.stringify({ action }),
  });

export const submitProjectStatus = async (payload: StatusUpdatePayload, tenantId?: string | null) =>
  apiFetch('/api/projects/status', {
    method: 'POST',
    tenantId,
    body: JSON.stringify(payload),
  });

export const fetchCanvasSnapshot = async (projectId: string, tenantId?: string | null) =>
  apiFetch(`/api/canvas/${projectId}`, { tenantId });

export const fetchProjectHealth = async (projectId: string, tenantId?: string | null) =>
  apiFetch(`/api/dashboard/${projectId}/health`, { tenantId });

export const fetchProjectKpis = async (projectId: string, tenantId?: string | null) =>
  apiFetch(`/api/dashboard/${projectId}/kpis`, { tenantId });

export const fetchHealthForecast = async (portfolioId: string = 'default', tenantId?: string | null) =>
  apiFetch(`/v1/predictive/health-forecast?portfolio_id=${encodeURIComponent(portfolioId)}`, { tenantId });
