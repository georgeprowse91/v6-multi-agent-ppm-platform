/**
 * Methodology Store - Zustand store for methodology navigation state
 */

import { create } from 'zustand';
import type {
  MethodologyActivity,
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
