import { requestJson } from '@/services/apiClient';

export type DocumentStatus = 'draft' | 'published';

export interface DocumentVersionPayload {
  projectId: string;
  documentKey: string;
  name: string;
  docType: string;
  classification: string;
  status: DocumentStatus;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface DocumentSummary {
  documentId: string;
  documentKey: string;
  projectId: string;
  name: string;
  docType: string;
  classification: string;
  latestVersion: number;
  latestStatus: DocumentStatus;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentVersion extends DocumentSummary {
  version: number;
  status: DocumentStatus;
  content: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface LessonPayload {
  projectId: string;
  stageId?: string | null;
  stageName?: string | null;
  title: string;
  description: string;
  tags: string[];
  topics: string[];
}

export interface LessonRecord {
  lessonId: string;
  projectId: string;
  stageId?: string | null;
  stageName?: string | null;
  title: string;
  description: string;
  tags: string[];
  topics: string[];
  createdAt: string;
  updatedAt: string;
}

export interface LessonRecommendationRequest {
  projectId: string;
  tags: string[];
  topics: string[];
  limit?: number;
}

const API_BASE = '/api/knowledge';

export async function createDocumentVersion(
  payload: DocumentVersionPayload
): Promise<DocumentVersion> {
  return requestJson<DocumentVersion>(`${API_BASE}/documents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: payload.projectId,
      document_key: payload.documentKey,
      name: payload.name,
      doc_type: payload.docType,
      classification: payload.classification,
      status: payload.status,
      content: payload.content,
      metadata: payload.metadata ?? {},
    }),
  });
}

export async function fetchDocuments(
  projectId: string,
  query?: string
): Promise<DocumentSummary[]> {
  const params = new URLSearchParams({ project_id: projectId });
  if (query) {
    params.set('query', query);
  }
  return requestJson<DocumentSummary[]>(`${API_BASE}/documents?${params.toString()}`);
}

export async function fetchDocumentVersions(
  documentId: string
): Promise<DocumentVersion[]> {
  return requestJson<DocumentVersion[]>(`${API_BASE}/documents/${documentId}/versions`);
}

export async function createLesson(payload: LessonPayload): Promise<LessonRecord> {
  return requestJson<LessonRecord>(`${API_BASE}/lessons`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: payload.projectId,
      stage_id: payload.stageId ?? null,
      stage_name: payload.stageName ?? null,
      title: payload.title,
      description: payload.description,
      tags: payload.tags,
      topics: payload.topics,
    }),
  });
}

export async function updateLesson(
  lessonId: string,
  payload: LessonPayload
): Promise<LessonRecord> {
  return requestJson<LessonRecord>(`${API_BASE}/lessons/${lessonId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: payload.projectId,
      stage_id: payload.stageId ?? null,
      stage_name: payload.stageName ?? null,
      title: payload.title,
      description: payload.description,
      tags: payload.tags,
      topics: payload.topics,
    }),
  });
}

export async function deleteLesson(lessonId: string): Promise<void> {
  await requestJson<void>(`${API_BASE}/lessons/${lessonId}`, {
    method: 'DELETE',
  });
}

export async function fetchLessons(
  projectId: string,
  query?: string,
  tags?: string[],
  topics?: string[]
): Promise<LessonRecord[]> {
  const params = new URLSearchParams({ project_id: projectId });
  if (query) params.set('query', query);
  if (tags && tags.length) params.set('tags', tags.join(','));
  if (topics && topics.length) params.set('topics', topics.join(','));
  return requestJson<LessonRecord[]>(`${API_BASE}/lessons?${params.toString()}`);
}

export async function fetchLessonRecommendations(
  payload: LessonRecommendationRequest
): Promise<LessonRecord[]> {
  return requestJson<LessonRecord[]>(`${API_BASE}/lessons/recommendations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: payload.projectId,
      tags: payload.tags,
      topics: payload.topics,
      limit: payload.limit ?? 5,
    }),
  });
}
