import { useCallback, useRef } from 'react';
import { useAssistantStore, type ActionChip, type PrerequisiteInfo } from '@/store/assistant';
import type { SuggestionApiResponse } from '@/store/assistant/types';
import type { MethodologyActivity, MethodologyStage } from '@/store/methodology';

interface GenerateSuggestionsArgs {
  activity: MethodologyActivity | null;
  stage: MethodologyStage | null;
  allActivities: MethodologyActivity[];
  allStages: MethodologyStage[];
  isLocked: boolean;
  incompletePrereqs: PrerequisiteInfo[];
  signal?: AbortSignal;
}

export function useSuggestionEngine() {
  const {
    actionChips,
    context,
    addAssistantMessage,
    setActionChips,
    clearActionChips,
    showGatingWarning,
  } = useAssistantStore();
  const inFlightByActivityRef = useRef<Map<string, Promise<ActionChip[]>>>(new Map());

  const generateSuggestions = useCallback(async ({
    activity,
    stage,
    isLocked,
    incompletePrereqs,
    signal,
  }: GenerateSuggestionsArgs) => {
    if (isLocked && activity && incompletePrereqs.length > 0) {
      showGatingWarning(activity, incompletePrereqs);
      return;
    }

    const activityKey = activity?.id ?? '__no_activity__';
    const existing = inFlightByActivityRef.current.get(activityKey);
    if (existing) {
      const dedupedChips = await existing;
      setActionChips(dedupedChips);
      return;
    }

    const request = (async () => {
      if (!context) {
        return [];
      }

      const payload = {
        project_id: context.projectId,
        activity_id: activity?.id ?? null,
        stage_id: stage?.id ?? null,
        activity_name: activity?.name ?? null,
        stage_name: stage?.name ?? null,
        activity_status: activity?.status ?? null,
        canvas_type: activity?.canvasType ?? null,
        incomplete_prerequisites: incompletePrereqs.map((prereq) => ({
          activity_id: prereq.activityId,
          activity_name: prereq.activityName,
          stage_id: prereq.stageId,
          stage_name: prereq.stageName,
          status: prereq.status,
        })),
      };

      try {
        const response = await fetch('/api/assistant/suggestions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal,
        });
        if (!response.ok) {
          return [];
        }
        const data = await response.json();
        if (!Array.isArray(data.suggestions) || data.suggestions.length === 0) {
          return [];
        }
        return data.suggestions.map((suggestion: SuggestionApiResponse) => ({
          id: suggestion.id,
          label: suggestion.label,
          category: suggestion.category,
          priority: suggestion.priority,
          icon: suggestion.icon,
          actionType: suggestion.action_type,
          payload: suggestion.payload,
          enabled: suggestion.enabled ?? true,
          description: suggestion.description,
        }));
      } catch (error) {
        if (signal?.aborted) {
          throw error;
        }
        console.warn('Failed to load assistant suggestions', error);
        return [];
      }
    })();

    inFlightByActivityRef.current.set(activityKey, request);

    try {
      const chips = await request;
      if (signal?.aborted) {
        return;
      }
      setActionChips(chips);
      if (chips.length > 0) {
        const message = activity
          ? `I see you're working on "${activity.name}". Here are some suggested actions:`
          : 'Here are some suggested actions to help you progress:';
        addAssistantMessage(message, chips);
      }
    } finally {
      inFlightByActivityRef.current.delete(activityKey);
    }
  }, [addAssistantMessage, context, setActionChips, showGatingWarning]);

  return {
    actionChips,
    isLoading: false,
    generateSuggestions,
    clearActionChips,
  };
}
