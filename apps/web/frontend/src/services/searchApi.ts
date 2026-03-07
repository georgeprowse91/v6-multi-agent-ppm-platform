export type SearchResultType =
  | 'document'
  | 'project'
  | 'knowledge'
  | 'approval'
  | 'workflow'
  | 'issues'
  | 'pages'
  | 'documents'
  | 'projects'
  | 'costs'
  | 'lists';

export type SourceSystem =
  | 'local'
  | 'jira'
  | 'confluence'
  | 'sharepoint'
  | 'sap';

export interface SearchResult {
  id: string;
  type: SearchResultType;
  title: string;
  summary: string;
  projectId?: string | null;
  updatedAt?: string | null;
  highlights?: Record<string, string> | null;
  payload: Record<string, unknown>;
  sourceSystem: SourceSystem;
  sourceUrl?: string | null;
}

export interface SearchResponse {
  query: string;
  offset: number;
  limit: number;
  total: number;
  results: SearchResult[];
  connectors: string[];
}

export interface SearchFilters {
  query: string;
  types?: SearchResultType[];
  projectIds?: string[];
  offset?: number;
  limit?: number;
  includeConnectors?: boolean;
}

const API_BASE = '/api/search';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Request failed');
  }
  return response.json() as Promise<T>;
}

export async function fetchGlobalSearch(
  filters: SearchFilters
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: filters.query });
  if (filters.types?.length) {
    params.set('types', filters.types.join(','));
  }
  if (filters.projectIds?.length) {
    params.set('project_ids', filters.projectIds.join(','));
  }
  if (filters.offset !== undefined) {
    params.set('offset', String(filters.offset));
  }
  if (filters.limit !== undefined) {
    params.set('limit', String(filters.limit));
  }
  if (filters.includeConnectors !== undefined) {
    params.set('include_connectors', String(filters.includeConnectors));
  }
  const response = await fetch(`${API_BASE}?${params.toString()}`);
  return handleResponse<SearchResponse>(response);
}
