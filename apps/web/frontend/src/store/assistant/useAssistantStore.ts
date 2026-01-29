/**
 * Assistant Store - Zustand store for AI assistant panel state
 *
 * Manages:
 * - Chat message history
 * - Current context (project, stage, activity)
 * - Next best action suggestions
 * - Gating warnings when prerequisites are incomplete
 */

import { create } from 'zustand';
import type {
  ActionChip,
  AssistantContext,
  AssistantMessage,
  PrerequisiteInfo,
  SuggestionTrigger,
} from './types';
import type { MethodologyActivity, MethodologyStage } from '../methodology/types';

interface AssistantStoreState {
  // Chat messages
  messages: AssistantMessage[];

  // Current context
  context: AssistantContext | null;

  // Current action chips (next best actions)
  actionChips: ActionChip[];

  // Loading state for suggestions
  isGeneratingSuggestions: boolean;

  // Actions - Messages
  addMessage: (message: Omit<AssistantMessage, 'id' | 'timestamp'>) => void;
  addUserMessage: (content: string) => void;
  addAssistantMessage: (content: string, actionChips?: ActionChip[], isWarning?: boolean) => void;
  addSystemMessage: (content: string) => void;
  clearMessages: () => void;

  // Actions - Context
  updateContext: (context: AssistantContext) => void;
  clearContext: () => void;

  // Actions - Action Chips
  setActionChips: (chips: ActionChip[]) => void;
  clearActionChips: () => void;
  executeActionChip: (chipId: string) => ActionChip | undefined;

  // Actions - Suggestions
  generateSuggestions: (
    trigger: SuggestionTrigger,
    activity: MethodologyActivity | null,
    stage: MethodologyStage | null,
    allActivities: MethodologyActivity[],
    allStages: MethodologyStage[],
    isLocked: boolean,
    incompletePrereqs: PrerequisiteInfo[]
  ) => Promise<void>;

  // Actions - Gating warnings
  showGatingWarning: (
    activity: MethodologyActivity,
    incompletePrereqs: PrerequisiteInfo[]
  ) => void;
}

export const useAssistantStore = create<AssistantStoreState>((set, get) => ({
  // Initial state
  messages: [],
  context: null,
  actionChips: [],
  isGeneratingSuggestions: false,

  // Message actions
  addMessage: (message) => {
    const newMessage: AssistantMessage = {
      ...message,
      id: crypto.randomUUID(),
      timestamp: new Date(),
    };
    set((state) => ({
      messages: [...state.messages, newMessage],
    }));
  },

  addUserMessage: (content) => {
    get().addMessage({ role: 'user', content });
  },

  addAssistantMessage: (content, actionChips, isWarning) => {
    const newMessage: AssistantMessage = {
      id: crypto.randomUUID(),
      timestamp: new Date(),
      role: 'assistant',
      content,
      actionChips,
      isWarning,
      context: get().context
        ? {
            activityId: get().context?.currentActivityId ?? undefined,
            activityName: get().context?.currentActivityName ?? undefined,
            stageId: get().context?.currentStageId ?? undefined,
            stageName: get().context?.currentStageName ?? undefined,
          }
        : undefined,
    };
    set((state) => ({
      messages: [...state.messages, newMessage],
      // Also update global action chips
      actionChips: actionChips ?? state.actionChips,
    }));
  },

  addSystemMessage: (content) => {
    get().addMessage({ role: 'system', content });
  },

  clearMessages: () => {
    set({ messages: [] });
  },

  // Context actions
  updateContext: (context) => {
    set({ context });
  },

  clearContext: () => {
    set({ context: null });
  },

  // Action chip actions
  setActionChips: (chips) => {
    set({ actionChips: chips });
  },

  clearActionChips: () => {
    set({ actionChips: [] });
  },

  executeActionChip: (chipId) => {
    const chip = get().actionChips.find((c) => c.id === chipId);
    if (chip) {
      // Log the action for chat history
      get().addUserMessage(`Selected: ${chip.label}`);
    }
    return chip;
  },

  // Generate suggestions based on current context
  generateSuggestions: async (
    _trigger,
    activity,
    stage,
    allActivities,
    allStages,
    isLocked,
    incompletePrereqs
  ) => {
    set({ isGeneratingSuggestions: true });

    // Handle locked activity - show gating warning
    if (isLocked && activity && incompletePrereqs.length > 0) {
      get().showGatingWarning(activity, incompletePrereqs);
      set({ isGeneratingSuggestions: false });
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

    const context = get().context;
    const payload = context
      ? {
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
        }
      : null;

    let chips = fallbackChips;
    if (payload) {
      try {
        const response = await fetch('/api/assistant/suggestions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (response.ok) {
          const data = await response.json();
          if (Array.isArray(data.suggestions) && data.suggestions.length > 0) {
            chips = data.suggestions.map((suggestion: any) => ({
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
          }
        }
      } catch (error) {
        console.warn('Failed to load assistant suggestions', error);
      }
    }

    set({
      actionChips: chips,
      isGeneratingSuggestions: false,
    });

    if (chips.length > 0) {
      const message = activity
        ? `I see you're working on "${activity.name}". Here are some suggested actions:`
        : 'Here are some suggested actions to help you progress:';
      get().addAssistantMessage(message, chips);
    }
  },

  // Show gating warning when prerequisites are incomplete
  showGatingWarning: (activity, incompletePrereqs) => {
    const prereqNames = incompletePrereqs.map((p) => p.activityName).join(', ');
    const warningMessage = `"${activity.name}" is not yet available. You need to complete the following prerequisite${
      incompletePrereqs.length > 1 ? 's' : ''
    } first: ${prereqNames}.`;

    // Create chips to navigate to prerequisites
    const chips: ActionChip[] = incompletePrereqs.map((prereq, index) => ({
      id: `prereq-${prereq.activityId}-${index}`,
      label: `Go to ${prereq.activityName}`,
      category: 'navigate',
      priority: 'high',
      icon: '→',
      actionType: 'open_activity',
      payload: {
        type: 'open_activity',
        activityId: prereq.activityId,
        stageId: prereq.stageId,
      },
      enabled: true,
      description: `Open ${prereq.activityName} in ${prereq.stageName}`,
    }));

    // Add chip to show all prerequisites
    if (incompletePrereqs.length > 1) {
      chips.push({
        id: 'show-all-prereqs',
        label: 'View all prerequisites',
        category: 'analyse',
        priority: 'medium',
        icon: '📋',
        actionType: 'show_prerequisites',
        payload: {
          type: 'show_prerequisites',
          activityId: activity.id,
          prerequisiteIds: incompletePrereqs.map((p) => p.activityId),
        },
        enabled: true,
        description: 'See the full list of prerequisites',
      });
    }

    set({ actionChips: chips });
    get().addAssistantMessage(warningMessage, chips, true);
  },
}));

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

  // Activity-specific suggestions based on activity ID
  switch (activity.id) {
    case 'act-budget':
      // Budget Planning - suggest generating template based on WBS
      const wbsActivity = allActivities.find((a) => a.id === 'act-wbs');
      if (wbsActivity?.status === 'complete') {
        chips.push({
          id: 'generate-budget-from-wbs',
          label: 'Generate budget template from WBS',
          category: 'create',
          priority: 'high',
          icon: '✨',
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
        icon: '📊',
        actionType: 'open_artifact',
        payload: {
          type: 'open_artifact',
          artifactId: activity.artifactId ?? 'new-budget',
        },
        enabled: true,
        description: 'Create a new budget from scratch',
      });
      break;

    case 'act-schedule':
      // Schedule - suggest generating from WBS
      const wbsForSchedule = allActivities.find((a) => a.id === 'act-wbs');
      if (wbsForSchedule?.status === 'complete') {
        chips.push({
          id: 'generate-schedule-from-wbs',
          label: 'Generate schedule from WBS',
          category: 'create',
          priority: 'high',
          icon: '✨',
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

    case 'act-wbs':
      // WBS - suggest reviewing charter first
      const charterActivity = allActivities.find((a) => a.id === 'act-charter');
      if (charterActivity?.status === 'complete') {
        chips.push({
          id: 'review-charter-for-wbs',
          label: 'Review Project Charter',
          category: 'review',
          priority: 'medium',
          icon: '👁',
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
        id: 'create-wbs',
        label: 'Create WBS structure',
        category: 'create',
        priority: 'high',
        icon: '🌳',
        actionType: 'open_artifact',
        payload: {
          type: 'open_artifact',
          artifactId: activity.artifactId ?? 'new-wbs',
        },
        enabled: true,
        description: 'Start building the Work Breakdown Structure',
      });
      break;

    case 'act-risk-plan':
      // Risk Management Plan
      chips.push({
        id: 'open-risk-register',
        label: 'Open Risk Register',
        category: 'navigate',
        priority: 'high',
        icon: '⚠',
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
      // Dashboard - suggest reviewing key metrics
      chips.push({
        id: 'view-schedule-status',
        label: 'View Schedule Status',
        category: 'analyse',
        priority: 'medium',
        icon: '📅',
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
        icon: '💰',
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
      // Generic suggestions based on activity status
      if (activity.status === 'not_started') {
        chips.push({
          id: `start-${activity.id}`,
          label: `Start ${activity.name}`,
          category: 'create',
          priority: 'high',
          icon: '▶',
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
          icon: '▶',
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
          label: `Mark as complete`,
          category: 'approve',
          priority: 'medium',
          icon: '✓',
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

  // Add next activity suggestion if current is complete or in progress
  if (activity.status === 'complete' || activity.status === 'in_progress') {
    const nextActivities = findNextActivities(activity, allActivities, allStages);
    nextActivities.slice(0, 2).forEach((next, index) => {
      chips.push({
        id: `next-activity-${next.id}-${index}`,
        label: `Go to ${next.name}`,
        category: 'navigate',
        priority: activity.status === 'complete' ? 'high' : 'low',
        icon: '→',
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

  // Always add dashboard option
  chips.push({
    id: 'open-dashboard',
    label: 'View Dashboard',
    category: 'navigate',
    priority: 'low',
    icon: '📈',
    actionType: 'open_dashboard',
    payload: {
      type: 'open_dashboard',
    },
    enabled: true,
    description: 'View project dashboard and metrics',
  });

  return chips;
}

/**
 * Generate general suggestions when no specific activity is selected
 */
function generateGeneralSuggestions(
  allActivities: MethodologyActivity[],
  _allStages: MethodologyStage[]
): ActionChip[] {
  const chips: ActionChip[] = [];

  // Find in-progress activities
  const inProgressActivities = allActivities.filter((a) => a.status === 'in_progress');
  inProgressActivities.slice(0, 2).forEach((activity, index) => {
    chips.push({
      id: `continue-${activity.id}-${index}`,
      label: `Continue ${activity.name}`,
      category: 'create',
      priority: 'high',
      icon: '▶',
      actionType: 'open_activity',
      payload: {
        type: 'open_activity',
        activityId: activity.id,
      },
      enabled: true,
      description: `Resume work on ${activity.name}`,
    });
  });

  // Find next available activity (not started, not locked)
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
      icon: '✨',
      actionType: 'open_activity',
      payload: {
        type: 'open_activity',
        activityId: nextActivity.id,
      },
      enabled: true,
      description: `Begin working on ${nextActivity.name}`,
    });
  }

  // Add dashboard option
  chips.push({
    id: 'open-dashboard',
    label: 'View Dashboard',
    category: 'navigate',
    priority: 'low',
    icon: '📈',
    actionType: 'open_dashboard',
    payload: {
      type: 'open_dashboard',
    },
    enabled: true,
    description: 'View project dashboard and metrics',
  });

  return chips;
}

/**
 * Find the next activities that depend on the current one
 */
function findNextActivities(
  currentActivity: MethodologyActivity,
  allActivities: MethodologyActivity[],
  _allStages: MethodologyStage[]
): MethodologyActivity[] {
  // Find activities that have the current activity as a prerequisite
  const dependentActivities = allActivities.filter(
    (a) =>
      a.prerequisites.includes(currentActivity.id) &&
      a.status !== 'complete'
  );

  // Also find next activities in the same stage by order
  const sameOrderNext = allActivities.filter(
    (a) =>
      a.order === currentActivity.order + 1 &&
      a.status !== 'complete'
  );

  // Combine and deduplicate
  const nextActivities = [...dependentActivities, ...sameOrderNext];
  const uniqueActivities = Array.from(
    new Map(nextActivities.map((a) => [a.id, a])).values()
  );

  return uniqueActivities;
}

export default useAssistantStore;
