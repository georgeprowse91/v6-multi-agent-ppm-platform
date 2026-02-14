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
import { projectApolloMethodology, methodologyTemplates } from './demoData';
import type { CanvasType } from '@ppm/canvas-engine';

interface WorkspaceActivitySummary {
  id: string;
  name: string;
  description: string;
  prerequisites: string[];
  category: string;
  recommended_canvas_tab: CanvasType;
  access: {
    allowed: boolean;
  };
  completed: boolean;
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
}

interface WorkspaceStateResponse {
  project_id: string;
  methodology: string | null;
  current_activity_id: string | null;
  available_methodologies: string[];
  methodology_map_summary: WorkspaceMethodologySummary;
}

const WORKSPACE_API_BASE = '/api/workspace';

function buildFallbackMethodology(methodologyId: string): MethodologyMap {
  const template = methodologyTemplates.find((item) => item.id === methodologyId) ?? methodologyTemplates[0];

  const stages = template.stages.map((stage, stageIndex) => {
    const parentActivityId = `${stage.id}-fallback-parent`;
    return {
      ...stage,
      order: stageIndex + 1,
      activities: [
        {
          id: parentActivityId,
          name: `${stage.name} Activity`,
          description: `Fallback activity for ${stage.name}`,
          status: 'not_started' as const,
          canvasType: 'document' as CanvasType,
          prerequisites: [],
          order: 1,
          children: [
            {
              id: `${parentActivityId}-child`,
              name: `${stage.name} Sub-activity`,
              description: `Fallback sub-activity for ${stage.name}`,
              status: 'not_started' as const,
              canvasType: 'document' as CanvasType,
              prerequisites: [],
              order: 1,
            },
          ],
        },
      ],
    };
  });

  return {
    ...template,
    stages,
  };
}

function summarizeActivityStatus(activity: WorkspaceActivitySummary): MethodologyStatus {
  if (activity.completed) return 'complete';
  if (!activity.access.allowed) return 'locked';
  return 'not_started';
}

function mapWorkspaceResponseToProjectMethodology(payload: WorkspaceStateResponse): ProjectMethodology {
  const methodologySummary = payload.methodology_map_summary;
  const stages: MethodologyStage[] = methodologySummary.stages.map((stage, stageIndex) => {
    const activities: MethodologyActivity[] = stage.activities.map((activity, activityIndex) => ({
      id: activity.id,
      name: activity.name,
      description: activity.description,
      status: summarizeActivityStatus(activity),
      canvasType: activity.recommended_canvas_tab,
      prerequisites: activity.prerequisites,
      order: activityIndex + 1,
      metadata: {
        category: activity.category,
      },
    }));

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
  // Initialize with Project Apollo demo data
  projectMethodology: projectApolloMethodology,
  availableMethodologies: ['predictive', 'adaptive', 'hybrid'],
  isHydrating: false,
  currentActivityId: projectApolloMethodology.currentActivityId,
  expandedStageIds: projectApolloMethodology.expandedStageIds,

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

  createFromTemplate: (templateId, projectId, projectName) => {
    const template = methodologyTemplates.find((t) => t.id === templateId);
    if (!template) return;

    // Deep clone the template
    const defaultExpandedStageIds = [
      template.stages[0]?.id,
      ...template.stages.filter((stage) => stage.alwaysAccessible).map((stage) => stage.id),
    ].filter((id, index, allIds): id is string => Boolean(id) && allIds.indexOf(id) === index);

    const newMethodology: ProjectMethodology = {
      projectId,
      projectName,
      methodology: JSON.parse(JSON.stringify(template)),
      currentActivityId: null,
      expandedStageIds: defaultExpandedStageIds,
    };

    set({
      projectMethodology: newMethodology,
      currentActivityId: null,
      expandedStageIds: newMethodology.expandedStageIds,
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
        isHydrating: false,
      });
    } catch (error) {
      const fallbackMethodologyId = methodology ?? get().projectMethodology.methodology.id;
      const fallbackMap = buildFallbackMethodology(fallbackMethodologyId);
      console.warn(
        `[methodology] Falling back to local demo methodology because backend workspace API is unavailable for project ${projectId}.`,
        error
      );
      set((state) => ({
        projectMethodology: {
          ...state.projectMethodology,
          projectId,
          methodology: fallbackMap,
          expandedStageIds: fallbackMap.stages.slice(0, 1).map((stage) => stage.id),
        },
        currentActivityId: null,
        expandedStageIds: fallbackMap.stages.slice(0, 1).map((stage) => stage.id),
        availableMethodologies: ['predictive', 'adaptive', 'hybrid'],
        isHydrating: false,
      }));
    }
  },

  // Selectors
  getStage: (stageId) => {
    return get().projectMethodology.methodology.stages.find((s) => s.id === stageId);
  },

  getActivity: (activityId) => {
    const stages = get().projectMethodology.methodology.stages;
    for (const stage of stages) {
      const activity = flattenMethodologyActivities(stage.activities).find((a) => a.id === activityId);
      if (activity) return activity;
    }
    return undefined;
  },

  getCurrentActivity: () => {
    const { currentActivityId } = get();
    if (!currentActivityId) return null;
    return get().getActivity(currentActivityId) ?? null;
  },

  getStageForActivity: (activityId) => {
    const stages = get().projectMethodology.methodology.stages;
    return stages.find((stage) =>
      flattenMethodologyActivities(stage.activities).some((a) => a.id === activityId)
    );
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
    return get().projectMethodology.methodology.stages.flatMap((stage) =>
      flattenMethodologyActivities(stage.activities)
    );
  },
}));
