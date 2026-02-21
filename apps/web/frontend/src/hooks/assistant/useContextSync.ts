import { useEffect, useRef } from 'react';
import type { AssistantContext, PrerequisiteInfo } from '@/store/assistant';
import type { MethodologyActivity, MethodologyStage } from '@/store/methodology';

interface UseContextSyncOptions {
  currentActivityId: string | null;
  buildContext: () => AssistantContext;
  updateContext: (context: AssistantContext) => void;
  getActivity: (activityId: string) => MethodologyActivity | undefined;
  getStageForActivity: (activityId: string) => MethodologyStage | undefined;
  getAllActivities: () => MethodologyActivity[];
  getAllStages: () => MethodologyStage[];
  isActivityLocked: (activityId: string) => boolean;
  getIncompletePrerequisites: (prerequisiteIds: string[], allActivities: MethodologyActivity[]) => PrerequisiteInfo[];
  clearActionChips: () => void;
  generateSuggestions: (args: {
    activity: MethodologyActivity | null;
    stage: MethodologyStage | null;
    allActivities: MethodologyActivity[];
    allStages: MethodologyStage[];
    isLocked: boolean;
    incompletePrereqs: PrerequisiteInfo[];
    signal?: AbortSignal;
  }) => Promise<void>;
}

export function useContextSync({
  currentActivityId,
  buildContext,
  updateContext,
  getActivity,
  getStageForActivity,
  getAllActivities,
  getAllStages,
  isActivityLocked,
  getIncompletePrerequisites,
  clearActionChips,
  generateSuggestions,
}: UseContextSyncOptions) {
  const prevActivityIdRef = useRef<string | null>(null);
  const suggestionAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    updateContext(buildContext());
  }, [buildContext, updateContext]);

  useEffect(() => {
    if (currentActivityId === prevActivityIdRef.current) {
      return;
    }
    prevActivityIdRef.current = currentActivityId;

    suggestionAbortRef.current?.abort();
    suggestionAbortRef.current = new AbortController();
    const signal = suggestionAbortRef.current.signal;

    const timeoutId = window.setTimeout(() => {
      if (!currentActivityId) {
        clearActionChips();
        return;
      }

      const activity = getActivity(currentActivityId);
      const stage = getStageForActivity(currentActivityId);
      if (!activity || !stage) return;

      const allActivities = getAllActivities();
      const incompletePrereqs = getIncompletePrerequisites(
        activity.prerequisites,
        allActivities
      );

      void generateSuggestions({
        activity,
        stage,
        allActivities,
        allStages: getAllStages(),
        isLocked: isActivityLocked(currentActivityId),
        incompletePrereqs,
        signal,
      });
    }, 150);

    return () => {
      window.clearTimeout(timeoutId);
      suggestionAbortRef.current?.abort();
    };
  }, [
    clearActionChips,
    currentActivityId,
    generateSuggestions,
    getActivity,
    getAllActivities,
    getAllStages,
    getIncompletePrerequisites,
    getStageForActivity,
    isActivityLocked,
  ]);
}
