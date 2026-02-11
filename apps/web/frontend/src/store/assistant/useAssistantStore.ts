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
  AIState,
  PrerequisiteInfo,
} from './types';
import type { MethodologyActivity } from '../methodology/types';

interface AssistantStoreState {
  // Chat messages
  messages: AssistantMessage[];

  // Current context
  context: AssistantContext | null;

  // Current action chips (next best actions)
  actionChips: ActionChip[];

  // Loading state for suggestions
  isGeneratingSuggestions: boolean;

  // Current AI state
  aiState: AIState;

  // Actions - Messages
  addMessage: (message: Omit<AssistantMessage, 'id' | 'timestamp'>) => void;
  addUserMessage: (content: string) => void;
  addAssistantMessage: (
    content: string,
    actionChips?: ActionChip[],
    isWarning?: boolean,
    overrides?: Partial<AssistantMessage>
  ) => void;
  addSystemMessage: (content: string) => void;
  clearMessages: () => void;

  // Actions - Context
  updateContext: (context: AssistantContext) => void;
  clearContext: () => void;

  // Actions - Action Chips
  setActionChips: (chips: ActionChip[]) => void;
  clearActionChips: () => void;
  executeActionChip: (chipId: string) => ActionChip | undefined;

  // Actions - Gating warnings
  showGatingWarning: (
    activity: MethodologyActivity,
    incompletePrereqs: PrerequisiteInfo[]
  ) => void;

  // Actions - AI state
  setAiState: (state: AIState) => void;
}

export const useAssistantStore = create<AssistantStoreState>((set, get) => ({
  // Initial state
  messages: [],
  context: null,
  actionChips: [],
  isGeneratingSuggestions: false,
  aiState: 'idle',

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

  addAssistantMessage: (content, actionChips, isWarning, overrides) => {
    const newMessage: AssistantMessage = {
      id: crypto.randomUUID(),
      timestamp: new Date(),
      role: 'assistant',
      content,
      actionChips,
      isWarning,
      aiState: get().aiState,
      sources: [],
      provenance: {
        generated: true,
        modelOrTool: 'PPM Assistant',
        showModelOrTool: false,
      },
      context: get().context
        ? {
            activityId: get().context?.currentActivityId ?? undefined,
            activityName: get().context?.currentActivityName ?? undefined,
            stageId: get().context?.currentStageId ?? undefined,
            stageName: get().context?.currentStageName ?? undefined,
          }
        : undefined,
      ...overrides,
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
      icon: 'navigation.next',
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
        icon: 'provenance.auditLog',
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

  setAiState: (state) => {
    set({ aiState: state });
  },
}));

export default useAssistantStore;
