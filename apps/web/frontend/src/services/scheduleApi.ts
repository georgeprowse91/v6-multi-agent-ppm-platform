export interface ScheduleTask {
  id: string;
  name: string;
  start: string;
  end: string;
  progress: number;
  dependencies: string[];
  owner: string;
  status: string;
}

export interface OptimizationSuggestion {
  id: string;
  type: 'parallel_tasks' | 'fast_track' | 'crash' | 'resource_level';
  description: string;
  affected_task_ids: string[];
  projected_saving_days: number;
  status: 'pending' | 'accepted' | 'rejected';
}

export interface OptimizeScheduleResponse {
  project_id: string;
  original_duration_days: number;
  optimized_duration_days: number;
  suggestions: OptimizationSuggestion[];
}

export interface ApplyOptimizationResponse {
  project_id: string;
  suggestion_id: string;
  action: string;
  updated_tasks: ScheduleTask[];
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Request failed');
  }
  return response.json() as Promise<T>;
}

export async function fetchScheduleOptimization(
  projectId: string,
): Promise<OptimizeScheduleResponse> {
  const response = await fetch(`/api/schedule/${projectId}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse<OptimizeScheduleResponse>(response);
}

export async function applyScheduleOptimization(
  projectId: string,
  suggestionId: string,
  action: 'accept' | 'reject',
): Promise<ApplyOptimizationResponse> {
  const response = await fetch(`/api/schedule/${projectId}/apply-optimization`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ suggestion_id: suggestionId, action }),
  });
  return handleResponse<ApplyOptimizationResponse>(response);
}
