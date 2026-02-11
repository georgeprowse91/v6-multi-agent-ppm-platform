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
    isGeneratingSuggestions,
  } = useAssistantStore();
  const inFlightByActivityRef = useRef<Map<string, Promise<ActionChip[]>>>(new Map());

  const generateSuggestions = useCallback(async ({
    activity,
    stage,
    allActivities,
    allStages,
    isLocked,
    incompletePrereqs,
    signal,
  }: GenerateSuggestionsArgs) => {
    useAssistantStore.setState({ isGeneratingSuggestions: true });

    if (isLocked && activity && incompletePrereqs.length > 0) {
      useAssistantStore.setState({ isGeneratingSuggestions: false });
      showGatingWarning(activity, incompletePrereqs);
      return;
    }

    const fallbackChips: ActionChip[] = [];
    if (activity && stage) {
      fallbackChips.push(
        ...generateActivitySuggestions(activity, stage, allActivities, allStages)
      );
    } else if (!activity) {
      fallbackChips.push(...generateGeneralSuggestions(allActivities, allStages));
    }

    const activityKey = activity?.id ?? '__no_activity__';
    const existing = inFlightByActivityRef.current.get(activityKey);
    if (existing) {
      const dedupedChips = await existing;
      setActionChips(dedupedChips);
      useAssistantStore.setState({ isGeneratingSuggestions: false });
      return;
    }

    const request = (async () => {
      if (!context) {
        return fallbackChips;
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
          return fallbackChips;
        }
        const data = await response.json();
        if (!Array.isArray(data.suggestions) || data.suggestions.length === 0) {
          return fallbackChips;
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
        return fallbackChips;
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
      useAssistantStore.setState({ isGeneratingSuggestions: false });
    }
  }, [addAssistantMessage, context, setActionChips, showGatingWarning]);

  return {
    actionChips,
    isLoading: isGeneratingSuggestions,
    generateSuggestions,
    clearActionChips,
  };
}

/**
 * Generate suggestions based on the current activity
 */
function generateActivitySuggestions(
  activity: MethodologyActivity,
  _stage: MethodologyStage,
  allActivities: MethodologyActivity[],
  allStages: MethodologyStage[]
): ActionChip[] {
  const chips: ActionChip[] = [];

  switch (activity.id) {
    case 'act-budget': {
      const wbsActivity = allActivities.find((a) => a.id === 'act-wbs');
      if (wbsActivity?.status === 'complete') {
        chips.push({
          id: 'generate-budget-from-wbs',
          label: 'Generate budget template from WBS',
          category: 'create',
          priority: 'high',
          icon: 'ai.suggestion',
          actionType: 'generate_template',
          payload: {
            type: 'generate_template',
            templateType: 'budget',
            basedOn: ['act-wbs'],
            targetActivityId: activity.id,
          },
          enabled: true,
          description: 'Create a budget structure based on your Work Breakdown Structure',
        });
      }
      chips.push({
        id: 'create-budget-manual',
        label: 'Start with blank budget',
        category: 'create',
        priority: 'medium',
        icon: 'artifact.spreadsheet',
        actionType: 'open_artifact',
        payload: {
          type: 'open_artifact',
          artifactId: activity.artifactId ?? 'new-budget',
        },
        enabled: true,
        description: 'Create a new budget from scratch',
      });
      break;
    }

    case 'act-schedule': {
      const wbsForSchedule = allActivities.find((a) => a.id === 'act-wbs');
      if (wbsForSchedule?.status === 'complete') {
        chips.push({
          id: 'generate-schedule-from-wbs',
          label: 'Generate schedule from WBS',
          category: 'create',
          priority: 'high',
          icon: 'ai.suggestion',
          actionType: 'generate_template',
          payload: {
            type: 'generate_template',
            templateType: 'schedule',
            basedOn: ['act-wbs'],
            targetActivityId: activity.id,
          },
          enabled: true,
          description: 'Create timeline based on Work Breakdown Structure tasks',
        });
      }
      break;
    }

    case 'act-wbs': {
      const charterActivity = allActivities.find((a) => a.id === 'act-charter');
      if (charterActivity?.status === 'complete') {
        chips.push({
          id: 'review-charter-for-wbs',
          label: 'Review Project Charter',
          category: 'review',
          priority: 'medium',
          icon: 'actions.preview',
          actionType: 'open_activity',
          payload: {
            type: 'open_activity',
            activityId: 'act-charter',
          },
          enabled: true,
          description: 'Review the charter to identify deliverables for WBS',
        });
      }
      chips.push({
        id: 'research-scope',
        label: 'Research scope with web sources',
        category: 'analyse',
        priority: 'medium',
        icon: 'actions.search',
        actionType: 'scope_research',
        payload: {
          type: 'scope_research',
        },
        enabled: true,
        description: 'Gather external references to refine scope and WBS items',
      });
      chips.push({
        id: 'create-wbs',
        label: 'Create WBS structure',
        category: 'create',
        priority: 'high',
        icon: 'artifact.tree',
        actionType: 'open_artifact',
        payload: {
          type: 'open_artifact',
          artifactId: activity.artifactId ?? 'new-wbs',
        },
        enabled: true,
        description: 'Start building the Work Breakdown Structure',
      });
      break;
    }

    case 'act-risk-plan':
      chips.push({
        id: 'open-risk-register',
        label: 'Open Risk Register',
        category: 'navigate',
        priority: 'high',
        icon: 'status.warning',
        actionType: 'open_activity',
        payload: {
          type: 'open_activity',
          activityId: 'act-risks',
        },
        enabled: true,
        description: 'View and manage project risks',
      });
      break;

    case 'act-dashboard':
      chips.push({
        id: 'view-schedule-status',
        label: 'View Schedule Status',
        category: 'analyse',
        priority: 'medium',
        icon: 'artifact.timeline',
        actionType: 'open_activity',
        payload: {
          type: 'open_activity',
          activityId: 'act-schedule',
        },
        enabled: true,
        description: 'Check the project timeline',
      });
      chips.push({
        id: 'view-budget-status',
        label: 'View Budget Status',
        category: 'analyse',
        priority: 'medium',
        icon: 'domain.budget',
        actionType: 'open_activity',
        payload: {
          type: 'open_activity',
          activityId: 'act-budget',
        },
        enabled: true,
        description: 'Check the project budget',
      });
      break;

    default:
      if (activity.status === 'not_started') {
        chips.push({
          id: `start-${activity.id}`,
          label: `Start ${activity.name}`,
          category: 'create',
          priority: 'high',
          icon: 'navigation.next',
          actionType: 'open_artifact',
          payload: {
            type: 'open_artifact',
            artifactId: activity.artifactId ?? `new-${activity.id}`,
          },
          enabled: true,
          description: `Begin working on ${activity.name}`,
        });
      } else if (activity.status === 'in_progress') {
        chips.push({
          id: `continue-${activity.id}`,
          label: `Continue ${activity.name}`,
          category: 'create',
          priority: 'high',
          icon: 'navigation.next',
          actionType: 'open_artifact',
          payload: {
            type: 'open_artifact',
            artifactId: activity.artifactId ?? `new-${activity.id}`,
          },
          enabled: true,
          description: `Continue working on ${activity.name}`,
        });
        chips.push({
          id: `complete-${activity.id}`,
          label: 'Mark as complete',
          category: 'approve',
          priority: 'medium',
          icon: 'actions.confirmApply',
          actionType: 'complete_activity',
          payload: {
            type: 'complete_activity',
            activityId: activity.id,
          },
          enabled: true,
          description: `Mark ${activity.name} as complete`,
        });
      }
  }

  if (activity.status === 'complete' || activity.status === 'in_progress') {
    const nextActivities = findNextActivities(activity, allActivities, allStages);
    nextActivities.slice(0, 2).forEach((next, index) => {
      chips.push({
        id: `next-activity-${next.id}-${index}`,
        label: `Go to ${next.name}`,
        category: 'navigate',
        priority: activity.status === 'complete' ? 'high' : 'low',
        icon: 'navigation.next',
        actionType: 'open_activity',
        payload: {
          type: 'open_activity',
          activityId: next.id,
        },
        enabled: true,
        description: `Continue to ${next.name}`,
      });
    });
  }

  chips.push({
    id: 'open-dashboard',
    label: 'View Dashboard',
    category: 'navigate',
    priority: 'low',
    icon: 'artifact.dashboard',
    actionType: 'open_dashboard',
    payload: {
      type: 'open_dashboard',
    },
    enabled: true,
    description: 'View project dashboard and metrics',
  });

  return chips;
}

function generateGeneralSuggestions(
  allActivities: MethodologyActivity[],
  _allStages: MethodologyStage[]
): ActionChip[] {
  const chips: ActionChip[] = [];

  const inProgressActivities = allActivities.filter((a) => a.status === 'in_progress');
  inProgressActivities.slice(0, 2).forEach((activity, index) => {
    chips.push({
      id: `continue-${activity.id}-${index}`,
      label: `Continue ${activity.name}`,
      category: 'create',
      priority: 'high',
      icon: 'navigation.next',
      actionType: 'open_activity',
      payload: {
        type: 'open_activity',
        activityId: activity.id,
      },
      enabled: true,
      description: `Resume work on ${activity.name}`,
    });
  });

  const notStartedActivities = allActivities.filter(
    (a) => a.status === 'not_started' && !a.prerequisites.length
  );
  if (notStartedActivities.length > 0) {
    const nextActivity = notStartedActivities[0];
    chips.push({
      id: `start-${nextActivity.id}`,
      label: `Start ${nextActivity.name}`,
      category: 'create',
      priority: 'medium',
      icon: 'ai.suggestion',
      actionType: 'open_activity',
      payload: {
        type: 'open_activity',
        activityId: nextActivity.id,
      },
      enabled: true,
      description: `Begin working on ${nextActivity.name}`,
    });
  }

  chips.push({
    id: 'open-dashboard',
    label: 'View Dashboard',
    category: 'navigate',
    priority: 'low',
    icon: 'artifact.dashboard',
    actionType: 'open_dashboard',
    payload: {
      type: 'open_dashboard',
    },
    enabled: true,
    description: 'View project dashboard and metrics',
  });

  return chips;
}

function findNextActivities(
  currentActivity: MethodologyActivity,
  allActivities: MethodologyActivity[],
  _allStages: MethodologyStage[]
): MethodologyActivity[] {
  const dependentActivities = allActivities.filter(
    (a) => a.prerequisites.includes(currentActivity.id) && a.status !== 'complete'
  );

  const sameOrderNext = allActivities.filter(
    (a) => a.order === currentActivity.order + 1 && a.status !== 'complete'
  );

  const nextActivities = [...dependentActivities, ...sameOrderNext];
  return Array.from(new Map(nextActivities.map((a) => [a.id, a])).values());
}
