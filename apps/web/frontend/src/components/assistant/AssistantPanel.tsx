import { useCallback, useEffect, useRef } from 'react';
import { createArtifact, createEmptyContent } from '@ppm/canvas-engine';
import { Icon } from '@/components/icon/Icon';
import { useAppStore } from '@/store/useAppStore';
import { useCanvasStore } from '@/store/useCanvasStore';
import { useMethodologyStore, type MethodologyActivity } from '@/store/methodology';
import {
  useAssistantStore,
  type ActionChip,
  type ConversationalCommandMessageData,
  type PrerequisiteInfo,
} from '@/store/assistant';
import { useAssistantChat } from './hooks/useAssistantChat';
import { useContextSync } from './hooks/useContextSync';
import { useSuggestionEngine } from './hooks/useSuggestionEngine';
import { AssistantHeader } from './AssistantHeader';
import { ContextBar } from './ContextBar';
import { MessageList } from './MessageList';
import { QuickActions } from './QuickActions';
import { ChatInput } from './ChatInput';
import styles from './AssistantPanel.module.css';
export function AssistantPanel() {
  const { rightPanelCollapsed, toggleRightPanel } = useAppStore();
  const { projectMethodology, currentActivityId, getActivity, getStageForActivity, isActivityLockedComputed, getAllActivities } = useMethodologyStore();
  const { artifacts, openArtifact } = useCanvasStore();
  const { messages, actionChips, context, aiState, typingStatus, addAssistantMessage, addSystemMessage, showGatingWarning, updateContext } = useAssistantStore();
  const { generateSuggestions, clearActionChips } = useSuggestionEngine();
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const onFallbackResponse = useCallback((text: string) => addAssistantMessage(`I heard: "${text}". Ask me to open an activity, dashboard, or /research.`), [addAssistantMessage]);
  const { sendMessage, error: assistantError } = useAssistantChat({ projectId: context?.projectId, onFallbackResponse });

  const buildContext = useCallback(() => {
    const activity = currentActivityId ? getActivity(currentActivityId) : null;
    const stage = currentActivityId ? getStageForActivity(currentActivityId) : null;
    return {
      projectId: projectMethodology.projectId,
      projectName: projectMethodology.projectName,
      methodologyName: projectMethodology.methodology.name,
      currentStageId: stage?.id ?? null,
      currentStageName: stage?.name ?? null,
      stageProgress: stage ? Math.round((stage.activities.filter((a) => a.status === 'complete').length / stage.activities.length) * 100) : 0,
      currentActivityId: activity?.id ?? null,
      currentActivityName: activity?.name ?? null,
      currentActivityStatus: activity?.status ?? null,
      currentActivityCanvasType: activity?.canvasType ?? null,
      isCurrentActivityLocked: currentActivityId ? isActivityLockedComputed(currentActivityId) : false,
      incompletePrerequisites: activity ? getIncompletePrerequisites(activity.prerequisites, getAllActivities()) : [],
    };
  }, [currentActivityId, getActivity, getAllActivities, getStageForActivity, isActivityLockedComputed, projectMethodology]);

  useContextSync({
    currentActivityId,
    buildContext,
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


  const previousContextEntityRef = useRef<string | null>(null);

  useEffect(() => {
    if (!context) return;
    const entity = context.currentActivityName ?? context.currentStageName ?? context.projectName;
    if (previousContextEntityRef.current && previousContextEntityRef.current !== entity) {
      addSystemMessage(`Context switched to ${entity}.`);
    }
    previousContextEntityRef.current = entity;
  }, [addSystemMessage, context]);

  const openForActivity = useCallback((activityId: string, stageId?: string) => {
    const activity = getActivity(activityId); if (!activity) return;
    if (isActivityLockedComputed(activityId)) return showGatingWarning(activity, getIncompletePrerequisites(activity.prerequisites, getAllActivities()));
    if (stageId) useMethodologyStore.getState().expandStage(stageId);
    useMethodologyStore.getState().setCurrentActivity(activityId);
    const artifact = activity.artifactId ? artifacts[activity.artifactId] : undefined;
    openArtifact(artifact ?? createArtifact(activity.canvasType, activity.name, projectMethodology.projectId, createEmptyContent(activity.canvasType)));
    addAssistantMessage(`Navigating to "${activity.name}".`);
  }, [addAssistantMessage, artifacts, getActivity, getAllActivities, isActivityLockedComputed, openArtifact, projectMethodology.projectId, showGatingWarning]);

  const handleChipClick = useCallback((chip: ActionChip) => {
    if (!chip.enabled) return;
    switch (chip.payload.type) {
      case 'open_activity': return openForActivity(chip.payload.activityId, chip.payload.stageId);
      case 'open_artifact': return currentActivityId ? openForActivity(currentActivityId) : undefined;
      case 'open_dashboard': return openForActivity('act-dashboard', 'stage-monitoring');
      case 'generate_template': return addAssistantMessage(`Template generation queued for ${chip.payload.templateType}.`);
      case 'show_prerequisites': return addAssistantMessage(`Prerequisites: ${chip.payload.prerequisiteIds.map((id) => getActivity(id)?.name).filter(Boolean).join(', ')}`);
      case 'complete_activity': useMethodologyStore.getState().updateActivityStatus(chip.payload.activityId, 'complete'); return addAssistantMessage(`Marked "${getActivity(chip.payload.activityId)?.name}" complete.`);
      case 'scope_research': return void sendMessage(chip.payload.objective ? `/research ${chip.payload.objective}` : '/research');
      case 'custom': {
        if (chip.payload.actionKey === 'ask_question') return inputRef.current?.focus();
        const data = (chip.payload.data ?? {}) as Partial<ConversationalCommandMessageData>;
        return addAssistantMessage('Review and confirm inline updates below.', undefined, false, {
          messageType: 'conversational_command',
          data: { title: data.title ?? chip.label, summary: data.summary, changes: data.changes ?? [] },
        });
      }
      default: return addAssistantMessage('Action executed.');
    }
  }, [addAssistantMessage, currentActivityId, getActivity, openForActivity, sendMessage]);

  if (rightPanelCollapsed) return <aside className={`${styles.panel} ${styles.collapsed}`} data-tour="assistant-panel"><button className={styles.expandButton} onClick={toggleRightPanel} title="Open Assistant"><Icon semantic="communication.message" label="Open Assistant" /></button></aside>;

  return (
    <aside className={styles.panel} data-tour="assistant-panel">
      <AssistantHeader title="Assistant" aiState={aiState} toggleRightPanel={toggleRightPanel} />
      {context && <ContextBar context={context} contextSyncLabel={context.currentActivityName ?? context.currentStageName ?? context.projectName} />}
      <MessageList messages={messages} aiState={aiState} typingStatus={typingStatus} context={context} onChipClick={handleChipClick} />
      <QuickActions chips={actionChips} onChipClick={handleChipClick} />
      <ChatInput error={assistantError} inputRef={inputRef} onSubmitMessage={sendMessage} onStartScopeResearch={() => void sendMessage('/research')} />
    </aside>
  );
}
function getIncompletePrerequisites(prerequisiteIds: string[], activities: MethodologyActivity[]): PrerequisiteInfo[] {
  const { getStageForActivity } = useMethodologyStore.getState();
  return prerequisiteIds.flatMap((id) => {
    const item = activities.find((a) => a.id === id);
    if (!item || item.status === 'complete') return [];
    const stage = getStageForActivity(id);
    return [{ activityId: item.id, activityName: item.name, status: item.status as PrerequisiteInfo['status'], stageId: stage?.id ?? '', stageName: stage?.name ?? '' }];
  });
}

export default AssistantPanel;
