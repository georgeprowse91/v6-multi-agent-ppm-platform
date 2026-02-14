/**
 * Methodology Store - Zustand store for methodology navigation state
 */

import { create } from 'zustand';
import type {
  MethodologyActivity,
  MethodologyMap,
  MethodologyStage,
  MethodologyStatus,
  ProjectMethodology,
} from './types';
import {
  calculateStageProgress,
  computeStageStatus,
  isActivityLocked,
  isStageLocked,
  flattenMethodologyActivities,
} from './types';
import type { CanvasType } from '@ppm/canvas-engine';
import { requestJson } from '@/services/apiClient';
import { useAssistantStore } from '@/store/assistant';

interface TemplateCanvasBinding {
  canvas_type: string;
  renderer_component: string;
  default_view: string;
}

interface TemplateMethodologyBinding {
  methodology_id: string;
  stage_id: string;
  activity_id: string;
  task_id: string | null;
  lifecycle_events: string[];
  required: boolean;
  gate_refs: string[];
}

interface TemplateMapping {
  template_id: string;
  name: string;
  version: number;
  methodology_bindings: TemplateMethodologyBinding[];
  canvas_binding: TemplateCanvasBinding;
}

interface WorkspaceActivitySummary {
  id: string;
  name: string;
  description: string;
  prerequisites: string[];
  category: string;
  recommended_canvas_tab: CanvasType;
  assistant_prompts: string[];
  template_id?: string | null;
  agent_id?: string | null;
  connector_id?: string | null;
  access: {
    allowed: boolean;
  };
  completed: boolean;
  children?: WorkspaceActivitySummary[];
}

interface WorkspaceStageSummary {
  id: string;
  name: string;
  activities: WorkspaceActivitySummary[];
}

interface WorkspaceMethodologySummary {
  id: string;
  name: string;
  description: string;
  stages: WorkspaceStageSummary[];
  monitoring?: WorkspaceActivitySummary[];
}

interface WorkspaceStateResponse {
  project_id: string;
  methodology: string | null;
  current_stage_id?: string | null;
  current_activity_id: string | null;
  available_methodologies: string[];
  methodology_map_summary: WorkspaceMethodologySummary;
  templates_available_here?: TemplateMapping[];
  templates_required_here?: TemplateMapping[];
  templates_in_review?: TemplateMapping[];
  runtime_actions_available?: string[];
  runtime_default_view_contract?: RuntimeResolutionContract | null;
}

interface RuntimeActionsResponse {
  actions: string[];
}

interface RuntimeResolveResponse {
  resolution_contract: RuntimeResolutionContract;
}

interface RuntimeActionResponse {
  workspace_id: string;
  lifecycle_event: string;
  assistant_response: {
    content: string | Record<string, unknown>;
    output_format: string;
  };
  status: string;
  human_review?: {
    status?: string;
    required?: boolean;
  };
}

interface RuntimeResolutionContract {
  canvas: {
    canvas_type: string;
    renderer_component: string;
    default_view: string;
    focus?: {
      template_id?: string;
      section?: string;
    };
  };
}

const WORKSPACE_API_BASE = '/api/workspace';


const emergencyFallbackMethodology: ProjectMethodology = {
  projectId: 'backend-unavailable',
  projectName: 'Backend unavailable',
  methodology: {
    id: 'unavailable',
    name: 'Backend Unavailable',
    description: 'Connect to the backend to load methodology stages and runtime contracts.',
    type: 'custom',
    version: 'emergency',
    stages: [],
    monitoring: [],
  },
  currentActivityId: null,
  expandedStageIds: [],
};

function buildEmergencyFallback(projectId: string): ProjectMethodology {
  return { ...emergencyFallbackMethodology, projectId, projectName: `Project ${projectId}` };
}

function summarizeActivityStatus(activity: WorkspaceActivitySummary): MethodologyStatus {
  if (activity.completed) return 'complete';
  if (!activity.access.allowed) return 'locked';
  return 'not_started';
}

function mapWorkspaceActivity(activity: WorkspaceActivitySummary, order: number, stageId?: string): MethodologyActivity {
  return {
    id: activity.id,
    name: activity.name,
    description: activity.description,
    status: summarizeActivityStatus(activity),
    canvasType: activity.recommended_canvas_tab,
    prerequisites: activity.prerequisites,
    order,
    metadata: {
      category: activity.category,
      assistant_suggested_actions: activity.assistant_prompts,
      template_id: activity.template_id ?? undefined,
      agent_id: activity.agent_id ?? undefined,
      connector_id: activity.connector_id ?? undefined,
      ...(stageId ? { stage_id: stageId } : {}),
    },
    children: (activity.children ?? []).map((child, childIndex) =>
      mapWorkspaceActivity(child, childIndex + 1, stageId)
    ),
  };
}

function mapWorkspaceResponseToProjectMethodology(payload: WorkspaceStateResponse): ProjectMethodology {
  const methodologySummary = payload.methodology_map_summary;
  const stages: MethodologyStage[] = methodologySummary.stages.map((stage, stageIndex) => {
    const activities: MethodologyActivity[] = stage.activities.map((activity, activityIndex) =>
      mapWorkspaceActivity(activity, activityIndex + 1, stage.id)
    );

    return {
      id: stage.id,
      name: stage.name,
      status: activities.some((activity) => activity.status === 'complete') ? 'in_progress' : 'not_started',
      activities,
      prerequisites: stageIndex > 0 ? [methodologySummary.stages[stageIndex - 1]?.id].filter(Boolean) : [],
      order: stageIndex + 1,
      alwaysAccessible: stage.name.toLowerCase().includes('monitoring'),
    };
  });


  const monitoring = (methodologySummary.monitoring ?? []).map((activity, activityIndex) => ({
    ...mapWorkspaceActivity(activity, activityIndex + 1, 'monitoring'),
    alwaysAccessible: true,
  }));

  const methodologyType = methodologySummary.id === 'predictive'
    ? 'predictive'
    : methodologySummary.id === 'adaptive'
      ? 'adaptive'
      : methodologySummary.id === 'hybrid'
        ? 'hybrid'
        : 'custom';

  return {
    projectId: payload.project_id,
    projectName: `Project ${payload.project_id}`,
    methodology: {
      id: methodologySummary.id,
      name: methodologySummary.name,
      description: methodologySummary.description,
      type: methodologyType,
      version: 'yaml-api',
      stages,
      monitoring,
    },
    currentActivityId: payload.current_activity_id,
    expandedStageIds: stages.slice(0, 1).map((stage) => stage.id),
  };
}

async function fetchWorkspaceState(projectId: string, methodology?: string): Promise<WorkspaceStateResponse> {
  const params = methodology ? `?methodology=${encodeURIComponent(methodology)}` : '';
  const relativeUrl = `${WORKSPACE_API_BASE}/${encodeURIComponent(projectId)}${params}`;
  const requestUrl = typeof window === 'undefined'
    ? `http://localhost${relativeUrl}`
    : new URL(relativeUrl, window.location.origin).toString();
  const response = await fetch(requestUrl);
  if (!response.ok) {
    throw new Error(`Failed to load workspace methodology (${response.status})`);
  }
  return response.json() as Promise<WorkspaceStateResponse>;
}


function updateActivityStatusInTree(
  activities: MethodologyActivity[],
  activityId: string,
  status: MethodologyStatus
): { activities: MethodologyActivity[]; updated: boolean } {
  let updated = false;

  const nextActivities = activities.map((activity) => {
    if (activity.id === activityId) {
      updated = true;
      return { ...activity, status };
    }

    if (!activity.children?.length) {
      return activity;
    }

    const nextChildResult = updateActivityStatusInTree(activity.children, activityId, status);
    if (!nextChildResult.updated) {
      return activity;
    }

    updated = true;
    return {
      ...activity,
      children: nextChildResult.activities,
    };
  });

  return { activities: nextActivities, updated };
}

interface MethodologyStoreState {
  templatesAvailableHere: TemplateMapping[];
  templatesRequiredHere: TemplateMapping[];
  templatesInReview: TemplateMapping[];
  runtimeActionsAvailable: string[];
  runtimeDefaultViewContract: RuntimeResolutionContract | null;
  backendReachable: boolean;

  // Current project methodology
  projectMethodology: ProjectMethodology;
  availableMethodologies: string[];
  isHydrating: boolean;

  // UI state
  currentActivityId: string | null;
  expandedStageIds: string[];

  // Actions - Navigation
  setCurrentActivity: (activityId: string | null) => void;
  toggleStageExpanded: (stageId: string) => void;
  expandStage: (stageId: string) => void;
  collapseStage: (stageId: string) => void;
  expandAllStages: () => void;
  collapseAllStages: () => void;

  // Actions - Status updates
  updateActivityStatus: (activityId: string, status: MethodologyStatus) => void;
  updateStageStatus: (stageId: string, status: MethodologyStatus) => void;

  // Actions - Methodology management
  loadProjectMethodology: (methodology: ProjectMethodology) => void;
  createFromTemplate: (templateId: string, projectId: string, projectName: string) => void;
  hydrateFromWorkspace: (projectId: string, methodology?: string) => Promise<void>;
  resolveNodeRuntime: (params: {
    methodologyId: string;
    stageId: string;
    activityId?: string | null;
    taskId?: string | null;
    event: 'view' | 'generate' | 'update' | 'review' | 'approve' | 'publish';
  }) => Promise<RuntimeResolutionContract | null>;
  executeNodeAction: (params: {
    workspaceId: string;
    methodologyId: string;
    stageId: string;
    activityId?: string | null;
    taskId?: string | null;
    lifecycleEvent: 'view' | 'generate' | 'update' | 'review' | 'approve' | 'publish';
    userInput?: Record<string, unknown>;
  }) => Promise<RuntimeActionResponse>;

  // Selectors
  getStage: (stageId: string) => MethodologyStage | undefined;
  getActivity: (activityId: string) => MethodologyActivity | undefined;
  getCurrentActivity: () => MethodologyActivity | null;
  getStageForActivity: (activityId: string) => MethodologyStage | undefined;
  isStageLockedComputed: (stageId: string) => boolean;
  isActivityLockedComputed: (activityId: string) => boolean;
  getStageProgressComputed: (stageId: string) => number;
  getAllActivities: () => MethodologyActivity[];
}

export const useMethodologyStore = create<MethodologyStoreState>((set, get) => ({
  // Initialize with an emergency fallback until workspace hydration completes
  projectMethodology: emergencyFallbackMethodology,
  availableMethodologies: ['predictive', 'adaptive', 'hybrid'],
  isHydrating: false,
  templatesAvailableHere: [],
  templatesRequiredHere: [],
  templatesInReview: [],
  runtimeActionsAvailable: [],
  runtimeDefaultViewContract: null,
  backendReachable: true,
  currentActivityId: emergencyFallbackMethodology.currentActivityId,
  expandedStageIds: emergencyFallbackMethodology.expandedStageIds,

  // Navigation actions
  setCurrentActivity: (activityId) => {
    set((state) => ({
      currentActivityId: activityId,
      projectMethodology: {
        ...state.projectMethodology,
        currentActivityId: activityId,
      },
    }));
  },

  toggleStageExpanded: (stageId) => {
    set((state) => {
      const isExpanded = state.expandedStageIds.includes(stageId);
      const newExpanded = isExpanded
        ? state.expandedStageIds.filter((id) => id !== stageId)
        : [...state.expandedStageIds, stageId];

      return {
        expandedStageIds: newExpanded,
        projectMethodology: {
          ...state.projectMethodology,
          expandedStageIds: newExpanded,
        },
      };
    });
  },

  expandStage: (stageId) => {
    set((state) => {
      if (state.expandedStageIds.includes(stageId)) return state;

      const newExpanded = [...state.expandedStageIds, stageId];
      return {
        expandedStageIds: newExpanded,
        projectMethodology: {
          ...state.projectMethodology,
          expandedStageIds: newExpanded,
        },
      };
    });
  },

  collapseStage: (stageId) => {
    set((state) => {
      const newExpanded = state.expandedStageIds.filter((id) => id !== stageId);
      return {
        expandedStageIds: newExpanded,
        projectMethodology: {
          ...state.projectMethodology,
          expandedStageIds: newExpanded,
        },
      };
    });
  },

  expandAllStages: () => {
    set((state) => {
      const allStageIds = state.projectMethodology.methodology.stages.map((s) => s.id);
      return {
        expandedStageIds: allStageIds,
        projectMethodology: {
          ...state.projectMethodology,
          expandedStageIds: allStageIds,
        },
      };
    });
  },

  collapseAllStages: () => {
    set((state) => ({
      expandedStageIds: [],
      projectMethodology: {
        ...state.projectMethodology,
        expandedStageIds: [],
      },
    }));
  },

  // Status update actions
  updateActivityStatus: (activityId, status) => {
    set((state) => {
      const newStages = state.projectMethodology.methodology.stages.map((stage) => {
        const nextActivityTree = updateActivityStatusInTree(stage.activities, activityId, status);
        if (!nextActivityTree.updated) return stage;

        // Recompute stage status based on activities
        const newStage = {
          ...stage,
          activities: nextActivityTree.activities,
        };
        newStage.status = computeStageStatus(newStage);

        return newStage;
      });

      return {
        projectMethodology: {
          ...state.projectMethodology,
          methodology: {
            ...state.projectMethodology.methodology,
            stages: newStages,
          },
        },
      };
    });
  },

  updateStageStatus: (stageId, status) => {
    set((state) => {
      const newStages = state.projectMethodology.methodology.stages.map((stage) => {
        if (stage.id !== stageId) return stage;
        return { ...stage, status };
      });

      return {
        projectMethodology: {
          ...state.projectMethodology,
          methodology: {
            ...state.projectMethodology.methodology,
            stages: newStages,
          },
        },
      };
    });
  },

  // Methodology management
  loadProjectMethodology: (methodology) => {
    set({
      projectMethodology: methodology,
      currentActivityId: methodology.currentActivityId,
      expandedStageIds: methodology.expandedStageIds,
    });
  },

  createFromTemplate: (_templateId, projectId, projectName) => {
    const fallback = buildEmergencyFallback(projectId);
    set({
      projectMethodology: { ...fallback, projectName },
      currentActivityId: null,
      expandedStageIds: [],
      backendReachable: false,
    });
  },

  hydrateFromWorkspace: async (projectId, methodology) => {
    set({ isHydrating: true });
    try {
      const payload = await fetchWorkspaceState(projectId, methodology);
      const mapped = mapWorkspaceResponseToProjectMethodology(payload);
      set({
        projectMethodology: mapped,
        currentActivityId: mapped.currentActivityId,
        expandedStageIds: mapped.expandedStageIds,
        availableMethodologies: payload.available_methodologies,
        templatesAvailableHere: payload.templates_available_here ?? [],
        templatesRequiredHere: payload.templates_required_here ?? [],
        templatesInReview: payload.templates_in_review ?? [],
        runtimeActionsAvailable: payload.runtime_actions_available ?? [],
        runtimeDefaultViewContract: payload.runtime_default_view_contract ?? null,
        backendReachable: true,
        isHydrating: false,
      });
    } catch (error) {
      console.warn(`[methodology] Backend workspace API unavailable for project ${projectId}.`, error);
      const fallback = buildEmergencyFallback(projectId);
      set({
        projectMethodology: fallback,
        currentActivityId: null,
        expandedStageIds: [],
        availableMethodologies: [],
        templatesAvailableHere: [],
        templatesRequiredHere: [],
        templatesInReview: [],
        runtimeActionsAvailable: [],
        runtimeDefaultViewContract: null,
        backendReachable: false,
        isHydrating: false,
      });
      useAssistantStore.getState().addAssistantMessage(
        'Backend is unreachable. Runtime actions are disabled until the API is available.',
        [],
        true
      );
    }
  },

  resolveNodeRuntime: async ({ methodologyId, stageId, activityId, taskId, event }) => {
    try {
      const query = new URLSearchParams({ methodology_id: methodologyId, stage_id: stageId });
      if (activityId) query.set('activity_id', activityId);
      if (taskId) query.set('task_id', taskId);

      const actionsPayload = await requestJson<RuntimeActionsResponse>(
        `/api/methodology/runtime/actions?${query.toString()}`
      );

      const resolveQuery = new URLSearchParams({ ...Object.fromEntries(query.entries()), event });
      const resolvedPayload = await requestJson<RuntimeResolveResponse>(
        `/api/methodology/runtime/resolve?${resolveQuery.toString()}`
      );

      set({
        runtimeActionsAvailable: actionsPayload.actions,
        runtimeDefaultViewContract: event === 'view' ? resolvedPayload.resolution_contract : get().runtimeDefaultViewContract,
        backendReachable: true,
      });

      return resolvedPayload.resolution_contract;
    } catch (error) {
      set({ runtimeActionsAvailable: [], backendReachable: false });
      useAssistantStore.getState().addAssistantMessage(
        'Unable to resolve runtime contract because the backend is unreachable. Actions are disabled.',
        [],
        true
      );
      return null;
    }
  },

  executeNodeAction: async ({ workspaceId, methodologyId, stageId, activityId, taskId, lifecycleEvent, userInput }) => {
    const payload = await requestJson<RuntimeActionResponse>('/api/methodology/runtime/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        methodology_id: methodologyId,
        stage_id: stageId,
        activity_id: activityId ?? null,
        task_id: taskId ?? null,
        lifecycle_event: lifecycleEvent,
        user_input: { ...(userInput ?? {}), workspace_id: workspaceId },
      }),
    });
    set({ backendReachable: true });
    return payload;
  },

  // Selectors
  getStage: (stageId) => {
    return get().projectMethodology.methodology.stages.find((s) => s.id === stageId);
  },

  getActivity: (activityId) => {
    const state = get();
    const stages = state.projectMethodology.methodology.stages;
    for (const stage of stages) {
      const activity = flattenMethodologyActivities(stage.activities).find((a) => a.id === activityId);
      if (activity) return activity;
    }
    return state.projectMethodology.methodology.monitoring.find((activity) => activity.id === activityId);
  },

  getCurrentActivity: () => {
    const { currentActivityId } = get();
    if (!currentActivityId) return null;
    return get().getActivity(currentActivityId) ?? null;
  },

  getStageForActivity: (activityId) => {
    const stages = get().projectMethodology.methodology.stages;
    const stage = stages.find((item) =>
      flattenMethodologyActivities(item.activities).some((a) => a.id === activityId)
    );
    if (stage) return stage;
    const monitoring = get().projectMethodology.methodology.monitoring;
    return monitoring.some((activity) => activity.id === activityId)
      ? {
          id: 'monitoring',
          name: 'Monitoring & Controlling',
          status: 'in_progress' as MethodologyStatus,
          activities: monitoring,
          prerequisites: [],
          order: Number.MAX_SAFE_INTEGER,
          alwaysAccessible: true,
        }
      : undefined;
  },

  isStageLockedComputed: (stageId) => {
    const state = get();
    const stage = state.getStage(stageId);
    if (!stage) return false;
    return isStageLocked(stage, state.projectMethodology.methodology.stages);
  },

  isActivityLockedComputed: (activityId) => {
    const state = get();
    const activity = state.getActivity(activityId);
    if (!activity) return false;

    // First check if the stage is locked
    const stage = state.getStageForActivity(activityId);
    if (stage && state.isStageLockedComputed(stage.id)) {
      return true;
    }

    return isActivityLocked(activity, state.getAllActivities());
  },

  getStageProgressComputed: (stageId) => {
    const stage = get().getStage(stageId);
    if (!stage) return 0;
    return calculateStageProgress(stage);
  },

  getAllActivities: () => {
    const methodology = get().projectMethodology.methodology;
    return [
      ...methodology.stages.flatMap((stage) => flattenMethodologyActivities(stage.activities)),
      ...flattenMethodologyActivities(methodology.monitoring),
    ];
  },
}));
