/**
 * AssistantPanel - AI assistant panel with context-aware suggestions
 *
 * Features:
 * - Context display (current project, stage, activity)
 * - Chat history with message list
 * - Next Best Actions chips
 * - Free text input
 * - Gating warnings when prerequisites are incomplete
 */

import { useRef, useCallback } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { useMethodologyStore, type MethodologyActivity } from '@/store/methodology';
import { useCanvasStore } from '@/store/useCanvasStore';
import {
  useAssistantStore,
  type ActionChip,
  type PrerequisiteInfo,
  type ScopeResearchItem,
  type ScopeResearchMessageData,
  type ConversationalCommandMessageData,
} from '@/store/assistant';
import { Icon } from '@/components/icon/Icon';
import { AssistantHeader } from './AssistantHeader';
import { ContextBar } from './ContextBar';
import { MessageList } from './MessageList';
import { ActionChipButton } from './ActionChipButton';
import { QuickActions } from './QuickActions';
import { ChatInput } from './ChatInput';
import { createArtifact, createEmptyContent } from '@ppm/canvas-engine';
import { useAssistantChat } from './hooks/useAssistantChat';
import { useContextSync } from './hooks/useContextSync';
import { useSuggestionEngine } from './hooks/useSuggestionEngine';
import styles from './AssistantPanel.module.css';

export function AssistantPanel() {
  const { rightPanelCollapsed, toggleRightPanel, featureFlags } = useAppStore();
  const {
    projectMethodology,
    currentActivityId,
    getActivity,
    getStageForActivity,
    isActivityLockedComputed,
    getAllActivities,
  } = useMethodologyStore();
  const { openArtifact, artifacts } = useCanvasStore();
  const {
    messages,
    context,
    addAssistantMessage,
    addSystemMessage,
    updateContext,
    showGatingWarning,
    aiState,
    setAiState,
  } = useAssistantStore();

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const conversationalCommandsEnabled = featureFlags.conversational_commands === true;


  const buildAssistantContext = useCallback(() => {
    const activity = currentActivityId ? getActivity(currentActivityId) : null;
    const stage = currentActivityId ? getStageForActivity(currentActivityId) : null;

    return {
      projectId: projectMethodology.projectId,
      projectName: projectMethodology.projectName,
      methodologyName: projectMethodology.methodology.name,
      currentStageId: stage?.id ?? null,
      currentStageName: stage?.name ?? null,
      stageProgress: stage
        ? Math.round(
            (stage.activities.filter((a) => a.status === 'complete').length /
              stage.activities.length) *
              100
          )
        : 0,
      currentActivityId: activity?.id ?? null,
      currentActivityName: activity?.name ?? null,
      currentActivityStatus: activity?.status ?? null,
      currentActivityCanvasType: activity?.canvasType ?? null,
      isCurrentActivityLocked: currentActivityId
        ? isActivityLockedComputed(currentActivityId)
        : false,
      incompletePrerequisites: activity
        ? getIncompletePrerequisites(activity.prerequisites, getAllActivities())
        : [],
    };
  }, [
    currentActivityId,
    getActivity,
    getAllActivities,
    getStageForActivity,
    isActivityLockedComputed,
    projectMethodology.methodology.name,
    projectMethodology.projectId,
    projectMethodology.projectName,
  ]);

  const { actionChips, generateSuggestions, clearActionChips } = useSuggestionEngine();

  useContextSync({
    currentActivityId,
    buildContext: buildAssistantContext,
    updateContext,
    getActivity,
    getStageForActivity,
    getAllActivities,
    getAllStages: () => projectMethodology.methodology.stages,
    isActivityLocked: isActivityLockedComputed,
    getIncompletePrerequisites,
    clearActionChips,
    generateSuggestions,
  });

  const buildScopeItems = (items: string[], prefix: string): ScopeResearchItem[] =>
    items.map((text, index) => ({
      id: `${prefix}-${index}`,
      text,
      status: 'pending',
    }));

  const applyScopeResearchSelections = useCallback((
    result: ScopeResearchMessageData,
    acceptedItems: ScopeResearchItem[]
  ) => {
    const confirmed = window.confirm(
      'Apply these scope updates to the project workspace?'
    );
    if (!confirmed) {
      return false;
    }

    addAssistantMessage(
      `Captured ${acceptedItems.length} scope items for review in the project workspace.`,
      undefined,
      false,
      { sources: result.sources ?? [] }
    );
    return true;
  }, [addAssistantMessage]);

  const startScopeResearch = useCallback(async (initialObjective?: string) => {
    if (!context?.projectId) {
      addAssistantMessage('Select a project before running scope research.');
      return;
    }

    const objectiveInput = (initialObjective ?? window.prompt('Enter a high-level objective for scope research:') ?? '').trim();
    if (!objectiveInput) {
      addAssistantMessage('Scope research was cancelled because no objective was provided.');
      return;
    }

    addSystemMessage('Starting scope research…');
    setAiState('tool_use');

    try {
      const response = await fetch(`/v1/projects/${context.projectId}/scope/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ objective: objectiveInput }),
      });
      if (!response.ok) {
        throw new Error('Scope research failed.');
      }
      const data = await response.json();
      const result: ScopeResearchMessageData = {
        objective: objectiveInput,
        scope: buildScopeItems(
          [
            ...(data.scope?.in_scope ?? []),
            ...(data.scope?.out_of_scope ?? []).map((item: string) => `Out of scope: ${item}`),
            ...(data.scope?.deliverables ?? []).map((item: string) => `Deliverable: ${item}`),
          ],
          'scope'
        ),
        requirements: buildScopeItems(data.requirements ?? [], 'req'),
        wbs: buildScopeItems(data.wbs ?? [], 'wbs'),
        sources: data.sources ?? [],
        notice: data.notice,
        usedExternalResearch: data.used_external_research ?? false,
      };

      addAssistantMessage('Scope research completed. Review and apply accepted items below.', undefined, false, {
        messageType: 'scope_research',
        data: result,
        sources: result.sources,
      });
      setAiState('completed');
    } catch (error) {
      addAssistantMessage('Scope research failed. Please try again.', undefined, true, {
        aiState: 'error',
      });
      setAiState('error');
    }
  }, [addAssistantMessage, addSystemMessage, context?.projectId, setAiState]);

  const clearConversationalCommandCardState = useCallback(() => {
    useAssistantStore.setState((state) => ({
      messages: state.messages.map((message) =>
        message.messageType === 'conversational_command'
          ? { ...message, messageType: 'default', data: undefined }
          : message
      ),
    }));
  }, []);

  const handleApplyConversationalCommand = useCallback((data: ConversationalCommandMessageData) => {
    const total = data.changes.length;
    addAssistantMessage(`Applied ${total} update${total === 1 ? '' : 's'} to ${data.title}.`);
    clearConversationalCommandCardState();
  }, [addAssistantMessage, clearConversationalCommandCardState]);

  // Handle chip click
  const handleChipClick = useCallback(
    (chip: ActionChip) => {
      if (!chip.enabled) return;

      // Execute the action based on chip type
      switch (chip.payload.type) {
        case 'open_activity': {
          const { activityId, stageId } = chip.payload;
          const activity = getActivity(activityId);
          if (!activity) return;

          // Check if locked
          const isLocked = isActivityLockedComputed(activityId);
          if (isLocked) {
            const prereqs = getIncompletePrerequisites(
              activity.prerequisites,
              getAllActivities()
            );
            showGatingWarning(activity, prereqs);
            return;
          }

          // Expand the stage if needed
          if (stageId) {
            useMethodologyStore.getState().expandStage(stageId);
          }

          // Set current activity
          useMethodologyStore.getState().setCurrentActivity(activityId);

          // Open artifact if exists
          if (activity.artifactId && artifacts[activity.artifactId]) {
            openArtifact(artifacts[activity.artifactId]);
          } else {
            // Create new artifact
            const newArtifact = createArtifact(
              activity.canvasType,
              activity.name,
              projectMethodology.projectId,
              createEmptyContent(activity.canvasType)
            );
            openArtifact(newArtifact);
          }

          addAssistantMessage(`Navigating to "${activity.name}".`);
          break;
        }

        case 'open_artifact': {
          const { artifactId } = chip.payload;
          if (artifacts[artifactId]) {
            openArtifact(artifacts[artifactId]);
            addAssistantMessage(`Opening artifact.`);
          } else {
            // Create new artifact for current activity
            const activity = currentActivityId
              ? getActivity(currentActivityId)
              : null;
            if (activity) {
              const newArtifact = createArtifact(
                activity.canvasType,
                activity.name,
                projectMethodology.projectId,
                createEmptyContent(activity.canvasType)
              );
              openArtifact(newArtifact);
              addAssistantMessage(`Created new ${activity.canvasType} artifact.`);
            }
          }
          break;
        }

        case 'open_dashboard': {
          const dashboardActivity = getActivity('act-dashboard');
          if (dashboardActivity) {
            useMethodologyStore.getState().setCurrentActivity('act-dashboard');
            useMethodologyStore.getState().expandStage('stage-monitoring');
            if (
              dashboardActivity.artifactId &&
              artifacts[dashboardActivity.artifactId]
            ) {
              openArtifact(artifacts[dashboardActivity.artifactId]);
            } else {
              const newArtifact = createArtifact(
                'dashboard',
                'Project Dashboard',
                projectMethodology.projectId,
                createEmptyContent('dashboard')
              );
              openArtifact(newArtifact);
            }
            addAssistantMessage('Opening the project dashboard.');
          }
          break;
        }

        case 'generate_template': {
          const { templateType, basedOn, targetActivityId } = chip.payload;
          const targetActivity = getActivity(targetActivityId);
          if (!targetActivity) return;

          // In this PR, we just add a message - actual generation would be backend
          const basedOnNames = basedOn
            ?.map((id) => getActivity(id)?.name)
            .filter(Boolean)
            .join(', ');

          addAssistantMessage(
            `I would generate a ${templateType} template${
              basedOnNames ? ` based on: ${basedOnNames}` : ''
            }. This feature will be available when connected to the backend.`,
            [
              {
                id: 'open-target-activity',
                label: `Open ${targetActivity.name}`,
                category: 'navigate',
                priority: 'high',
                icon: 'navigation.next',
                actionType: 'open_activity',
                payload: {
                  type: 'open_activity',
                  activityId: targetActivityId,
                },
                enabled: true,
              },
            ]
          );
          break;
        }

        case 'show_prerequisites': {
          const { activityId, prerequisiteIds } = chip.payload;
          const activity = getActivity(activityId);
          const prereqNames = prerequisiteIds
            .map((id) => getActivity(id)?.name)
            .filter(Boolean);
          addAssistantMessage(
            `Prerequisites for "${activity?.name}": ${prereqNames.join(', ')}`,
            prerequisiteIds.map((prereqId, index) => ({
              id: `prereq-${prereqId}-${index}`,
              label: `Go to ${getActivity(prereqId)?.name}`,
              category: 'navigate' as const,
              priority: 'high' as const,
              icon: 'navigation.next',
              actionType: 'open_activity' as const,
              payload: {
                type: 'open_activity' as const,
                activityId: prereqId,
              },
              enabled: true,
            }))
          );
          break;
        }

        case 'complete_activity': {
          const { activityId } = chip.payload;
          useMethodologyStore.getState().updateActivityStatus(activityId, 'complete');
          const activity = getActivity(activityId);
          addAssistantMessage(`Marked "${activity?.name}" as complete.`);
          break;
        }

        case 'scope_research': {
          void startScopeResearch(chip.payload.objective);
          break;
        }

        case 'custom': {
          if (chip.payload.actionKey === 'start_first_activity') {
            const firstActivity = getAllActivities().find(
              (activity) => activity.id !== 'act-dashboard'
            );
            if (firstActivity) {
              handleChipClick({
                id: `start-${firstActivity.id}`,
                label: `Open ${firstActivity.name}`,
                category: 'navigate',
                priority: 'high',
                actionType: 'open_activity',
                payload: {
                  type: 'open_activity',
                  activityId: firstActivity.id,
                },
                enabled: true,
              });
            }
            break;
          }

          if (chip.payload.actionKey === 'ask_question') {
            inputRef.current?.focus();
            addAssistantMessage('What would you like to know about your project?');
            break;
          }

          if (chip.payload.actionKey !== 'conversational_command') {
            addAssistantMessage('Action executed.');
            break;
          }
          if (!conversationalCommandsEnabled) {
            addAssistantMessage('Conversational commands are disabled for this workspace.');
            break;
          }
          const data = (chip.payload.data ?? {}) as Partial<ConversationalCommandMessageData>;
          const changes = Array.isArray(data.changes)
            ? data.changes.map((change, index) => ({
                id: change.id ?? `change-${index}`,
                label: change.label ?? `Change ${index + 1}`,
                before: change.before,
                after: change.after,
                status: change.status,
              }))
            : [];

          addAssistantMessage('Review and confirm these updates before applying.', undefined, false, {
            messageType: 'conversational_command',
            data: {
              title: data.title ?? 'Review conversational updates',
              summary: data.summary,
              changes,
              applyLabel: data.applyLabel,
            },
          });
          break;
        }

        default:
          addAssistantMessage('Action executed.');
      }
    },
    [
      getActivity,
      isActivityLockedComputed,
      getAllActivities,
      showGatingWarning,
      artifacts,
      openArtifact,
      projectMethodology.projectId,
      addAssistantMessage,
      currentActivityId,
      startScopeResearch,
      conversationalCommandsEnabled,
    ]
  );

  const handleLocalResponse = useCallback((userInput: string) => {
    const input = userInput.toLowerCase();

    if (input.includes('help') || input.includes('what can')) {
      addAssistantMessage(
        'I can help you navigate the project methodology, suggest next actions, and warn you about prerequisites. Try clicking on different activities in the left panel to see context-aware suggestions!',
        [
          {
            id: 'open-dashboard-help',
            label: 'View Dashboard',
            category: 'navigate',
            priority: 'medium',
            icon: 'artifact.dashboard',
            actionType: 'open_dashboard',
            payload: { type: 'open_dashboard' },
            enabled: true,
          },
        ]
      );
    } else if (input.includes('budget')) {
      const budgetActivity = getActivity('act-budget');
      if (budgetActivity) {
        const isLocked = isActivityLockedComputed('act-budget');
        if (isLocked) {
          const prereqs = getIncompletePrerequisites(
            budgetActivity.prerequisites,
            getAllActivities()
          );
          showGatingWarning(budgetActivity, prereqs);
        } else {
          addAssistantMessage('Here are options for budget planning:', [
            {
              id: 'go-to-budget',
              label: 'Open Budget Plan',
              category: 'navigate',
              priority: 'high',
              icon: 'domain.budget',
              actionType: 'open_activity',
              payload: { type: 'open_activity', activityId: 'act-budget' },
              enabled: true,
            },
            {
              id: 'generate-budget',
              label: 'Generate from WBS',
              category: 'create',
              priority: 'high',
              icon: 'ai.suggestion',
              actionType: 'generate_template',
              payload: {
                type: 'generate_template',
                templateType: 'budget',
                basedOn: ['act-wbs'],
                targetActivityId: 'act-budget',
              },
              enabled: true,
            },
          ]);
        }
      }
    } else if (input.includes('schedule') || input.includes('timeline')) {
      const scheduleActivity = getActivity('act-schedule');
      if (scheduleActivity) {
        const isLocked = isActivityLockedComputed('act-schedule');
        if (isLocked) {
          const prereqs = getIncompletePrerequisites(
            scheduleActivity.prerequisites,
            getAllActivities()
          );
          showGatingWarning(scheduleActivity, prereqs);
        } else {
          addAssistantMessage('Here are options for schedule planning:', [
            {
              id: 'go-to-schedule',
              label: 'Open Project Schedule',
              category: 'navigate',
              priority: 'high',
              icon: 'artifact.timeline',
              actionType: 'open_activity',
              payload: { type: 'open_activity', activityId: 'act-schedule' },
              enabled: true,
            },
          ]);
        }
      }
    } else if (input.includes('wbs') || input.includes('breakdown')) {
      addAssistantMessage('Let me help you with the Work Breakdown Structure:', [
        {
          id: 'go-to-wbs',
          label: 'Open WBS',
          category: 'navigate',
          priority: 'high',
          icon: 'artifact.tree',
          actionType: 'open_activity',
          payload: { type: 'open_activity', activityId: 'act-wbs' },
          enabled: true,
        },
      ]);
    } else if (input.includes('risk')) {
      addAssistantMessage('Here are risk management options:', [
        {
          id: 'go-to-risks',
          label: 'Open Risk Register',
          category: 'navigate',
          priority: 'high',
          icon: 'status.warning',
          actionType: 'open_activity',
          payload: { type: 'open_activity', activityId: 'act-risks' },
          enabled: true,
        },
      ]);
    } else if (context?.currentActivityName) {
      addAssistantMessage(
        `You're currently working on "${context.currentActivityName}". How can I help you with this activity?`
      );
    } else {
      addAssistantMessage(
        'Select an activity from the methodology panel to see context-aware suggestions, or ask me about budget, schedule, WBS, or risks.'
      );
    }
  }, [
    addAssistantMessage,
    context?.currentActivityName,
    getActivity,
    getAllActivities,
    isActivityLockedComputed,
    showGatingWarning,
  ]);

  const { sendMessage, error: assistantError } = useAssistantChat({
    projectId: context?.projectId,
    onFallbackResponse: handleLocalResponse,
  });

  // Collapsed state
  if (rightPanelCollapsed) {
    return (
      <aside className={`${styles.panel} ${styles.collapsed}`} data-tour="assistant-panel">
        <button
          className={styles.expandButton}
          onClick={toggleRightPanel}
          title="Open Assistant"
        >
          <Icon
            semantic="communication.message"
            label="Open Assistant"
          />
        </button>
      </aside>
    );
  }

  return (
    <aside className={styles.panel} data-tour="assistant-panel">
      {/* Header */}
      <AssistantHeader
        title="Assistant"
        aiState={aiState}
        toggleRightPanel={toggleRightPanel}
      />

      {/* Context Display */}
      {context && <ContextBar context={context} />}

      {/* Messages */}
      <MessageList
        messages={messages}
        aiState={aiState}
        context={context}
        onChipClick={handleChipClick}
        renderActionChip={(chip, options) => (
          <ActionChipButton
            chip={chip}
            onClick={() => handleChipClick(chip)}
            small={options?.small}
          />
        )}
        onApplyScopeResearch={applyScopeResearchSelections}
        onApplyConversationalCommand={handleApplyConversationalCommand}
        onCancelConversationalCommand={clearConversationalCommandCardState}
      />

      <QuickActions chips={actionChips} onChipClick={handleChipClick} />

      {/* Input Area */}
      <ChatInput
        error={assistantError}
        inputRef={inputRef}
        onSubmitMessage={sendMessage}
        onStartScopeResearch={() => void startScopeResearch()}
      />
    </aside>
  );
}


/**
 * Helper: Get incomplete prerequisites with full info
 */
function getIncompletePrerequisites(
  prerequisiteIds: string[],
  allActivitiesOrFn: MethodologyActivity[] | (() => MethodologyActivity[])
): PrerequisiteInfo[] {
  const methodologyStore = useMethodologyStore.getState();
  const activitiesArray = typeof allActivitiesOrFn === 'function'
    ? allActivitiesOrFn()
    : allActivitiesOrFn;

  const result: PrerequisiteInfo[] = [];

  for (const prereqId of prerequisiteIds) {
    const prereq = activitiesArray.find((a) => a.id === prereqId);
    if (!prereq || prereq.status === 'complete') continue;

    const stage = methodologyStore.getStageForActivity(prereqId);
    result.push({
      activityId: prereq.id,
      activityName: prereq.name,
      status: prereq.status as PrerequisiteInfo['status'],
      stageId: stage?.id ?? '',
      stageName: stage?.name ?? '',
    });
  }

  return result;
}

export default AssistantPanel;
