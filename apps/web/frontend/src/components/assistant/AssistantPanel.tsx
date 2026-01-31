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

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { useMethodologyStore, type MethodologyActivity } from '@/store/methodology';
import { useCanvasStore } from '@/store/useCanvasStore';
import type { PromptDefinition } from '@/types/prompt';
import {
  useAssistantStore,
  CATEGORY_COLORS,
  CATEGORY_ICONS,
  type ActionChip,
  type AssistantMessage,
  type PrerequisiteInfo,
} from '@/store/assistant';
import { createArtifact, createEmptyContent } from '@ppm/canvas-engine';
import promptsData from '../../../../data/prompts.json';
import styles from './AssistantPanel.module.css';

type ScopeResearchStatus = 'pending' | 'accepted' | 'rejected';
type ScopeResearchSection = 'scope' | 'requirements' | 'wbs';

interface ScopeResearchItem {
  id: string;
  text: string;
  status: ScopeResearchStatus;
}

interface ScopeResearchResult {
  scope: ScopeResearchItem[];
  requirements: ScopeResearchItem[];
  wbs: ScopeResearchItem[];
  sources: string[];
  notice?: string;
  usedExternalResearch: boolean;
}

const ALWAYS_INCLUDED_PROMPTS = new Set<string>(['risk_identification', 'vendor_evaluation']);

const stageTagLookup: Array<{ matcher: RegExp; tag: string }> = [
  { matcher: /initiation/i, tag: 'initiation' },
  { matcher: /planning/i, tag: 'planning' },
  { matcher: /execution/i, tag: 'execution' },
  { matcher: /monitoring/i, tag: 'monitoring' },
  { matcher: /controlling/i, tag: 'monitoring' },
  { matcher: /closing/i, tag: 'closing' },
];

export function AssistantPanel() {
  const { rightPanelCollapsed, toggleRightPanel } = useAppStore();
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
    actionChips,
    context,
    addUserMessage,
    addAssistantMessage,
    updateContext,
    generateSuggestions,
    showGatingWarning,
    clearActionChips,
  } = useAssistantStore();

  const [inputValue, setInputValue] = useState('');
  const [scopeResearchOpen, setScopeResearchOpen] = useState(false);
  const [scopeResearchObjective, setScopeResearchObjective] = useState('');
  const [scopeResearchLoading, setScopeResearchLoading] = useState(false);
  const [scopeResearchError, setScopeResearchError] = useState<string | null>(null);
  const [scopeResearchResult, setScopeResearchResult] = useState<ScopeResearchResult | null>(
    null
  );
  const [promptSearch, setPromptSearch] = useState('');
  const [selectedPrompt, setSelectedPrompt] = useState<PromptDefinition | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const prevActivityIdRef = useRef<string | null>(null);

  const promptStageTags = useMemo(() => {
    const candidates = [context?.currentStageName ?? '', context?.currentStageId ?? ''];
    const tags = new Set<string>();
    for (const value of candidates) {
      stageTagLookup.forEach(({ matcher, tag }) => {
        if (matcher.test(value)) {
          tags.add(tag);
        }
      });
    }
    return Array.from(tags);
  }, [context?.currentStageId, context?.currentStageName]);

  const promptChips = useMemo(() => {
    const prompts = promptsData as PromptDefinition[];
    const normalizedSearch = promptSearch.trim().toLowerCase();

    return prompts.filter((prompt) => {
      const matchesAlways =
        ALWAYS_INCLUDED_PROMPTS.has(prompt.id) || prompt.tags.includes('general');
      const matchesStage =
        promptStageTags.length === 0 ||
        prompt.tags.some((tag) => promptStageTags.includes(tag));

      if (!matchesAlways && !matchesStage) {
        return false;
      }

      if (!normalizedSearch) {
        return true;
      }

      const searchTarget = [
        prompt.id,
        prompt.label,
        prompt.description,
        prompt.tags.join(' '),
      ]
        .join(' ')
        .toLowerCase();

      return searchTarget.includes(normalizedSearch);
    });
  }, [promptSearch, promptStageTags]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Update context when activity changes
  useEffect(() => {
    const activity = currentActivityId ? getActivity(currentActivityId) : null;
    const stage = currentActivityId ? getStageForActivity(currentActivityId) : null;

    updateContext({
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
    });
  }, [
    currentActivityId,
    projectMethodology,
    getActivity,
    getStageForActivity,
    isActivityLockedComputed,
    getAllActivities,
    updateContext,
  ]);

  // Generate suggestions when activity changes
  useEffect(() => {
    // Only trigger if activity actually changed
    if (currentActivityId === prevActivityIdRef.current) return;
    prevActivityIdRef.current = currentActivityId;

    if (!currentActivityId) {
      clearActionChips();
      return;
    }

    const activity = getActivity(currentActivityId);
    const stage = getStageForActivity(currentActivityId);
    if (!activity || !stage) return;

    const isLocked = isActivityLockedComputed(currentActivityId);
    const allActivities = getAllActivities();
    const incompletePrereqs = getIncompletePrerequisites(
      activity.prerequisites,
      allActivities
    );

    // Generate suggestions based on context
    generateSuggestions(
      'activity_selected',
      activity,
      stage,
      allActivities,
      projectMethodology.methodology.stages,
      isLocked,
      incompletePrereqs
    );
  }, [
    currentActivityId,
    getActivity,
    getStageForActivity,
    isActivityLockedComputed,
    getAllActivities,
    generateSuggestions,
    clearActionChips,
    projectMethodology.methodology.stages,
  ]);

  const buildScopeItems = (items: string[], prefix: string): ScopeResearchItem[] =>
    items.map((text, index) => ({
      id: `${prefix}-${index}`,
      text,
      status: 'pending',
    }));

  const updateScopeItem = (
    section: ScopeResearchSection,
    id: string,
    updates: Partial<ScopeResearchItem>
  ) => {
    setScopeResearchResult((prev) => {
      if (!prev) return prev;
      const updatedSection = (prev[section] as ScopeResearchItem[]).map((item) =>
        item.id === id ? { ...item, ...updates } : item
      );
      return { ...prev, [section]: updatedSection } as ScopeResearchResult;
    });
  };

  const handleScopeResearchSubmit = async () => {
    if (!context?.projectId) {
      addAssistantMessage('Select a project before running scope research.');
      return;
    }
    if (!scopeResearchObjective.trim()) {
      setScopeResearchError('Please enter a high-level objective.');
      return;
    }

    setScopeResearchLoading(true);
    setScopeResearchError(null);
    setScopeResearchResult(null);

    try {
      const response = await fetch(`/api/v1/projects/${context.projectId}/scope/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ objective: scopeResearchObjective.trim() }),
      });
      if (!response.ok) {
        throw new Error('Scope research failed.');
      }
      const data = await response.json();
      setScopeResearchResult({
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
      });
      if (data.notice) {
        addAssistantMessage(data.notice);
      }
    } catch (error) {
      setScopeResearchError('Unable to complete scope research. Please try again.');
      addAssistantMessage('Scope research failed. Please try again.', undefined, true);
    } finally {
      setScopeResearchLoading(false);
    }
  };

  const renderResearchSection = (
    title: string,
    section: ScopeResearchSection,
    items: ScopeResearchItem[]
  ) => (
    <div className={styles.researchSection}>
      <h4 className={styles.researchSectionTitle}>{title}</h4>
      {items.length === 0 ? (
        <p className={styles.researchEmpty}>No suggestions yet.</p>
      ) : (
        items.map((item) => (
          <div key={item.id} className={styles.researchItem}>
            <input
              className={styles.researchInput}
              value={item.text}
              onChange={(event) =>
                updateScopeItem(section, item.id, { text: event.target.value })
              }
            />
            <div className={styles.researchActions}>
              <button
                type="button"
                className={`${styles.researchAction} ${
                  item.status === 'accepted' ? styles.researchActionActive : ''
                }`}
                onClick={() => updateScopeItem(section, item.id, { status: 'accepted' })}
              >
                Accept
              </button>
              <button
                type="button"
                className={`${styles.researchAction} ${
                  item.status === 'rejected' ? styles.researchActionReject : ''
                }`}
                onClick={() => updateScopeItem(section, item.id, { status: 'rejected' })}
              >
                Reject
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );

  const handlePromptClick = (prompt: PromptDefinition) => {
    setInputValue(prompt.description);
    setSelectedPrompt(prompt);
    inputRef.current?.focus();
  };

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
                icon: '→',
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
              icon: '→',
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
          setScopeResearchObjective(chip.payload.objective ?? '');
          setScopeResearchResult(null);
          setScopeResearchError(null);
          setScopeResearchOpen(true);
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
      setScopeResearchObjective,
    ]
  );

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextValue = event.target.value;
    setInputValue(nextValue);
    if (selectedPrompt && nextValue.trim() !== selectedPrompt.description.trim()) {
      setSelectedPrompt(null);
    }
  };

  // Handle text input submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    addUserMessage(inputValue.trim());

    // Simple local response (no backend in this PR)
    setTimeout(() => {
      handleLocalResponse(inputValue.trim());
    }, 300);

    setInputValue('');
    setSelectedPrompt(null);
  };

  // Handle local responses without backend
  const handleLocalResponse = (userInput: string) => {
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
            icon: '📈',
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
              icon: '💰',
              actionType: 'open_activity',
              payload: { type: 'open_activity', activityId: 'act-budget' },
              enabled: true,
            },
            {
              id: 'generate-budget',
              label: 'Generate from WBS',
              category: 'create',
              priority: 'high',
              icon: '✨',
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
              icon: '📅',
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
          icon: '🌳',
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
          icon: '⚠',
          actionType: 'open_activity',
          payload: { type: 'open_activity', activityId: 'act-risks' },
          enabled: true,
        },
      ]);
    } else {
      // Default response with current context
      if (context?.currentActivityName) {
        addAssistantMessage(
          `You're currently working on "${context.currentActivityName}". How can I help you with this activity?`
        );
      } else {
        addAssistantMessage(
          'Select an activity from the methodology panel to see context-aware suggestions, or ask me about budget, schedule, WBS, or risks.'
        );
      }
    }
  };

  // Collapsed state
  if (rightPanelCollapsed) {
    return (
      <aside className={`${styles.panel} ${styles.collapsed}`}>
        <button
          className={styles.expandButton}
          onClick={toggleRightPanel}
          title="Open Assistant"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </aside>
    );
  }

  return (
    <aside className={styles.panel}>
      {/* Header */}
      <div className={styles.header}>
        <h2 className={styles.title}>Assistant</h2>
        <button
          className={styles.collapseButton}
          onClick={toggleRightPanel}
          title="Close Assistant"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>

      {/* Context Display */}
      {context && (
        <div className={styles.contextArea}>
          <div className={styles.contextHeader}>
            <span className={styles.contextLabel}>Current Context</span>
          </div>
          <div className={styles.contextContent}>
            <div className={styles.contextItem}>
              <span className={styles.contextItemLabel}>Project</span>
              <span className={styles.contextItemValue}>{context.projectName}</span>
            </div>
            {context.currentStageName && (
              <div className={styles.contextItem}>
                <span className={styles.contextItemLabel}>Stage</span>
                <span className={styles.contextItemValue}>
                  {context.currentStageName}
                  <span className={styles.progressBadge}>{context.stageProgress}%</span>
                </span>
              </div>
            )}
            {context.currentActivityName && (
              <div className={styles.contextItem}>
                <span className={styles.contextItemLabel}>Activity</span>
                <span
                  className={`${styles.contextItemValue} ${
                    context.isCurrentActivityLocked ? styles.locked : ''
                  }`}
                >
                  {context.currentActivityName}
                  {context.isCurrentActivityLocked && (
                    <span className={styles.lockedBadge}>Locked</span>
                  )}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Chips (Next Best Actions) */}
      {actionChips.length > 0 && (
        <div className={styles.chipsArea}>
          <div className={styles.chipsHeader}>
            <span className={styles.chipsLabel}>Suggested Actions</span>
          </div>
          <div className={styles.chipsList}>
            {actionChips.map((chip) => (
              <ActionChipButton
                key={chip.id}
                chip={chip}
                onClick={() => handleChipClick(chip)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Prompt Library */}
      <div className={styles.promptArea}>
        <div className={styles.chipsHeader}>
          <span className={styles.chipsLabel}>Next actions</span>
        </div>
        <input
          type="search"
          className={styles.promptSearch}
          placeholder="Search prompt library..."
          value={promptSearch}
          onChange={(event) => setPromptSearch(event.target.value)}
          aria-label="Search prompt library"
        />
        {promptChips.length === 0 ? (
          <p className={styles.promptEmpty}>No prompts match this stage yet.</p>
        ) : (
          <div className={styles.promptChipsList}>
            {promptChips.map((prompt) => (
              <button
                key={prompt.id}
                type="button"
                className={styles.promptChip}
                onClick={() => handlePromptClick(prompt)}
                title={prompt.description}
              >
                <span className={styles.promptChipLabel}>{prompt.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Messages */}
      <div className={styles.messages}>
        {messages.length === 0 ? (
          <div className={styles.empty}>
            <svg
              width="48"
              height="48"
              viewBox="0 0 20 20"
              fill="currentColor"
              className={styles.emptyIcon}
            >
              <path
                fillRule="evenodd"
                d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z"
                clipRule="evenodd"
              />
            </svg>
            <p className={styles.emptyText}>
              Select an activity from the methodology panel to see context-aware
              suggestions, or type a question below.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onChipClick={handleChipClick}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form className={styles.inputArea} onSubmit={handleSubmit}>
        <input
          type="text"
          className={styles.input}
          placeholder="Ask about your project..."
          value={inputValue}
          onChange={handleInputChange}
          ref={inputRef}
        />
        <button
          type="submit"
          className={styles.sendButton}
          disabled={!inputValue.trim()}
          title="Send message"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>
        </button>
      </form>

      {scopeResearchOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <h3>Scope research</h3>
              <button
                type="button"
                className={styles.modalClose}
                onClick={() => setScopeResearchOpen(false)}
              >
                ✕
              </button>
            </div>
            <p className={styles.modalHint}>
              Enter a high-level objective to research scope, requirements, and WBS proposals.
            </p>
            <textarea
              className={styles.modalTextarea}
              value={scopeResearchObjective}
              onChange={(event) => setScopeResearchObjective(event.target.value)}
              placeholder="e.g., Launch a compliant customer self-service portal."
            />
            {scopeResearchError && (
              <p className={styles.researchError}>{scopeResearchError}</p>
            )}
            <div className={styles.modalActions}>
              <button
                type="button"
                className={styles.modalPrimary}
                onClick={handleScopeResearchSubmit}
                disabled={scopeResearchLoading}
              >
                {scopeResearchLoading ? 'Researching…' : 'Run research'}
              </button>
            </div>

            {scopeResearchResult && (
              <div className={styles.researchResults}>
                {scopeResearchResult.notice && (
                  <p className={styles.researchNotice}>{scopeResearchResult.notice}</p>
                )}
                {renderResearchSection(
                  'Scope statements',
                  'scope',
                  scopeResearchResult.scope
                )}
                {renderResearchSection(
                  'Requirements',
                  'requirements',
                  scopeResearchResult.requirements
                )}
                {renderResearchSection('WBS items', 'wbs', scopeResearchResult.wbs)}
                {scopeResearchResult.sources.length > 0 && (
                  <div className={styles.researchSources}>
                    <h4>Sources</h4>
                    <ul>
                      {scopeResearchResult.sources.map((source) => (
                        <li key={source}>{source}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className={styles.modalActions}>
                  <button
                    type="button"
                    className={styles.modalSecondary}
                    onClick={() => {
                      const acceptedCount = [
                        ...scopeResearchResult.scope,
                        ...scopeResearchResult.requirements,
                        ...scopeResearchResult.wbs,
                      ].filter((item) => item.status === 'accepted').length;
                      addAssistantMessage(
                        `Captured ${acceptedCount} scope items for review in the project workspace.`
                      );
                      setScopeResearchOpen(false);
                    }}
                  >
                    Apply selections
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}

/**
 * Message bubble component
 */
interface MessageBubbleProps {
  message: AssistantMessage;
  onChipClick: (chip: ActionChip) => void;
}

function MessageBubble({ message, onChipClick }: MessageBubbleProps) {
  return (
    <div
      className={`${styles.message} ${styles[message.role]} ${
        message.isWarning ? styles.warning : ''
      }`}
    >
      <div className={styles.messageContent}>{message.content}</div>
      {message.actionChips && message.actionChips.length > 0 && (
        <div className={styles.messageChips}>
          {message.actionChips.map((chip) => (
            <ActionChipButton
              key={chip.id}
              chip={chip}
              onClick={() => onChipClick(chip)}
              small
            />
          ))}
        </div>
      )}
      <time className={styles.messageTime}>
        {message.timestamp.toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        })}
      </time>
    </div>
  );
}

/**
 * Action chip button component
 */
interface ActionChipButtonProps {
  chip: ActionChip;
  onClick: () => void;
  small?: boolean;
}

function ActionChipButton({ chip, onClick, small = false }: ActionChipButtonProps) {
  const colors = CATEGORY_COLORS[chip.category];
  const icon = chip.icon ?? CATEGORY_ICONS[chip.category];

  return (
    <button
      className={`${styles.chip} ${small ? styles.chipSmall : ''} ${
        !chip.enabled ? styles.chipDisabled : ''
      }`}
      onClick={onClick}
      disabled={!chip.enabled}
      title={chip.description}
      style={{
        backgroundColor: colors.bg,
        color: colors.text,
        borderColor: colors.border,
      }}
    >
      <span className={styles.chipIcon}>{icon}</span>
      <span className={styles.chipLabel}>{chip.label}</span>
    </button>
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
