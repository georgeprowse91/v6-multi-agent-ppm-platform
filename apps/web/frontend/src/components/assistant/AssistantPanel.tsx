import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
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
import { useIntakeAssistantAdapter } from './hooks/useIntakeAssistantAdapter';
import { AssistantHeader } from './AssistantHeader';
import { ContextBar } from './ContextBar';
import { MessageList } from './MessageList';
import { QuickActions } from './QuickActions';
import { ChatInput } from './ChatInput';
import { ENTRY_ASSISTANT_CHIPS } from './entryQuickActions';
import type { WorkspaceType } from './entryQuickActions';
import { resolveAssistantMode } from './assistantMode';
import { useIntakeAssistantStore } from '@/store/assistant/useIntakeAssistantStore';
import styles from './AssistantPanel.module.css';

interface DemoScriptMessage {
  role: 'user' | 'assistant';
  content: string;
}

type DemoScenarioId = 'project_intake' | 'resource_request' | 'vendor_procurement';

const DEMO_SCENARIOS: Array<{ id: DemoScenarioId; label: string }> = [
  { id: 'project_intake', label: 'Project Intake' },
  { id: 'resource_request', label: 'Resource Request' },
  { id: 'vendor_procurement', label: 'Vendor Procurement' },
];

function isDemoModeEnabled(): boolean {
  const env = import.meta.env as Record<string, unknown>;
  const value = env.DEMO_MODE ?? env.VITE_DEMO_MODE;
  return ['1', 'true', 'yes', 'on'].includes(String(value ?? '').toLowerCase());
}

export function AssistantPanel() {
  const navigate = useNavigate();
  const location = useLocation();
  const { rightPanelCollapsed, toggleRightPanel } = useAppStore();
  const { projectMethodology, currentActivityId, getActivity, getStageForActivity, isActivityLockedComputed, getAllActivities } = useMethodologyStore();
  const { artifacts, openArtifact } = useCanvasStore();
  const {
    messages,
    actionChips,
    context,
    mode,
    aiState,
    typingStatus,
    addUserMessage,
    addAssistantMessage,
    addSystemMessage,
    showGatingWarning,
    updateContext,
    clearMessages,
    setActionChips,
    setMode,
  } = useAssistantStore();
  const { generateSuggestions, clearActionChips } = useSuggestionEngine();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const demoMode = useMemo(() => isDemoModeEnabled(), []);
  const [demoScenario, setDemoScenario] = useState<DemoScenarioId>('project_intake');
  const [demoScript, setDemoScript] = useState<DemoScriptMessage[]>([]);
  const [demoStepIndex, setDemoStepIndex] = useState(0);
  const [demoLoading, setDemoLoading] = useState(false);
  const [pendingWorkspaceType, setPendingWorkspaceType] = useState<WorkspaceType | null>(null);
  const intakeActive = mode === 'intake';
  const enqueuePatch = useIntakeAssistantStore((state) => state.enqueuePatch);
  const { sendIntakeMessage } = useIntakeAssistantAdapter(intakeActive);

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

  useEffect(() => {
    const nextMode = resolveAssistantMode(location.pathname);
    if (nextMode !== mode) {
      setMode(nextMode);
    }

    if (nextMode === 'entry') {
      setActionChips(ENTRY_ASSISTANT_CHIPS);
      return;
    }

    clearActionChips();
  }, [clearActionChips, location.pathname, mode, setActionChips, setMode]);

  const restartDemoScenario = useCallback((script: DemoScriptMessage[]) => {
    clearActionChips();
    clearMessages();
    let idx = 0;
    while (idx < script.length && script[idx]?.role === 'assistant') {
      addAssistantMessage(script[idx].content);
      idx += 1;
      if (idx > 0) break;
    }
    setDemoStepIndex(idx);
  }, [addAssistantMessage, clearActionChips, clearMessages]);

  useEffect(() => {
    if (!demoMode) return;
    let cancelled = false;
    setDemoLoading(true);

    fetch(`/api/assistant/demo-conversations/${demoScenario}`)
      .then(async (response) => {
        if (!response.ok) throw new Error('Unable to load scenario.');
        return response.json();
      })
      .then((payload: { messages?: DemoScriptMessage[] }) => {
        if (cancelled) return;
        const script = Array.isArray(payload.messages) ? payload.messages : [];
        setDemoScript(script);
        restartDemoScenario(script);
      })
      .catch(() => {
        if (cancelled) return;
        setDemoScript([]);
        clearMessages();
        addAssistantMessage('Demo scenario could not be loaded.');
        setDemoStepIndex(0);
      })
      .finally(() => {
        if (!cancelled) setDemoLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [addAssistantMessage, clearMessages, demoMode, demoScenario, restartDemoScenario]);

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
        if (chip.payload.actionKey === 'navigate_intake') {
          setPendingWorkspaceType(null);
          navigate('/intake/new', { state: { resetAt: Date.now() } });
          return;
        }
        if (chip.payload.actionKey === 'open_workspace') {
          const rawWorkspaceType = chip.payload.data?.workspaceType;
          const workspaceType = rawWorkspaceType === 'portfolio' || rawWorkspaceType === 'program' || rawWorkspaceType === 'project'
            ? rawWorkspaceType
            : null;
          if (!workspaceType) {
            addAssistantMessage('I could not determine which workspace type to open.');
            return;
          }

          setPendingWorkspaceType(null);
          navigate(`/${workspaceType}s`);
          addAssistantMessage(`Opening the ${workspaceType} workspace directory.`);
          return;
        }
        if (chip.payload.actionKey === 'methodology_runtime_action') {
          const lifecycleEvent = chip.payload.data?.lifecycleEvent;
          const stageId = chip.payload.data?.stageId;
          const activityId = chip.payload.data?.activityId;
          if (typeof lifecycleEvent !== 'string' || typeof stageId !== 'string' || typeof activityId !== 'string') {
            addAssistantMessage('Unable to run this lifecycle action.');
            return;
          }
          const methodologyState = useMethodologyStore.getState();
          void methodologyState.executeNodeAction({
            workspaceId: methodologyState.projectMethodology.projectId,
            methodologyId: methodologyState.projectMethodology.methodology.id,
            stageId,
            activityId,
            lifecycleEvent: lifecycleEvent as 'generate' | 'update' | 'review' | 'approve' | 'publish' | 'view',
          }).then(async (response) => {
            if (response.human_review?.required) {
              addAssistantMessage('Action submitted and pending human review.');
              return;
            }
            const contract = await methodologyState.resolveNodeRuntime({
              methodologyId: methodologyState.projectMethodology.methodology.id,
              stageId,
              activityId,
              event: 'view',
            });
            const activity = methodologyState.getActivity(activityId);
            if (!activity || !contract) return;
            openArtifact(createArtifact(activity.canvasType, activity.name, methodologyState.projectMethodology.projectId, createEmptyContent(activity.canvasType)));
            addAssistantMessage(`${lifecycleEvent} completed for ${activity.name}.`);
          }).catch(() => addAssistantMessage('Lifecycle action failed.'));
          return;
        }
        if (chip.payload.actionKey === 'ask_question') return inputRef.current?.focus();
        if (chip.payload.actionKey === 'intake_apply_field') {
          const field = typeof chip.payload.data?.field === 'string' ? chip.payload.data.field : '';
          const value = typeof chip.payload.data?.value === 'string' ? chip.payload.data.value : '';
          if (!field) {
            addAssistantMessage('Unable to apply this proposal because the target field is missing.');
            return;
          }
          enqueuePatch(field, value);
          addAssistantMessage(`Queued update for ${field}. Review the form confirmation prompt to apply it.`);
          return;
        }
        const data = (chip.payload.data ?? {}) as Partial<ConversationalCommandMessageData>;
        return addAssistantMessage('Review and confirm inline updates below.', undefined, false, {
          messageType: 'conversational_command',
          data: { title: data.title ?? chip.label, summary: data.summary, changes: data.changes ?? [] },
        });
      }
      default: return addAssistantMessage('Action executed.');
    }
  }, [addAssistantMessage, currentActivityId, enqueuePatch, getActivity, navigate, openForActivity, sendMessage]);

  const demoBranchReply = useCallback((input: string) => {
    const normalized = input.toLowerCase();
    if (demoScenario === 'project_intake' && demoStepIndex === 3 && normalized.includes('onboarding')) {
      return 'Great choice. I captured the objective as cutting onboarding cycle time by 30% in two quarters. Do you want me to draft an intake summary now?';
    }
    if (demoScenario === 'resource_request' && demoStepIndex === 3 && normalized.includes('backfill')) {
      return 'Understood. I can prepare a hiring backfill brief with lead-time assumptions and milestone risk impact. Should I proceed?';
    }
    if (demoScenario === 'vendor_procurement' && demoStepIndex === 3 && normalized.includes('fast')) {
      return 'Got it. I will optimize for fast go-live and streamline legal review checkpoints. Do you want a draft evaluation scorecard?';
    }
    return null;
  }, [demoScenario, demoStepIndex]);

  const handleSubmitMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (pendingWorkspaceType) {
      if (!trimmed) {
        addAssistantMessage(`Enter a ${pendingWorkspaceType} ID and I will open that workspace.`);
        return;
      }
      addUserMessage(trimmed);
      setPendingWorkspaceType(null);
      navigate(`/${pendingWorkspaceType}/${encodeURIComponent(trimmed)}`);
      addAssistantMessage(`Opening ${pendingWorkspaceType} workspace ${trimmed}.`);
      return;
    }

    if (intakeActive) {
      await sendIntakeMessage(text);
      return;
    }

    if (!demoMode) {
      await sendMessage(text);
      return;
    }

    if (!trimmed) return;
    addUserMessage(trimmed);

    const expected = demoScript[demoStepIndex];
    if (!expected) {
      addAssistantMessage('This scripted demo is complete. Restart or choose another scenario.');
      return;
    }

    if (expected.role !== 'user') {
      addAssistantMessage('Please restart the demo scenario to continue this scripted flow.');
      return;
    }

    const branchReply = demoBranchReply(trimmed);
    if (branchReply) {
      addAssistantMessage(branchReply);
      setDemoStepIndex(Math.min(demoStepIndex + 2, demoScript.length));
      return;
    }

    const normalized = trimmed.toLowerCase();
    const expectedText = expected.content.toLowerCase();
    const matchesExpected = normalized.includes(expectedText) || expectedText.includes(normalized);
    if (!matchesExpected) {
      addAssistantMessage('For this demo script, try the suggested response path or pick the alternate branch option.');
      return;
    }

    let idx = demoStepIndex + 1;
    while (idx < demoScript.length && demoScript[idx]?.role === 'assistant') {
      addAssistantMessage(demoScript[idx].content);
      idx += 1;
    }
    setDemoStepIndex(idx);
  }, [addAssistantMessage, addUserMessage, demoBranchReply, demoMode, demoScript, demoStepIndex, intakeActive, navigate, pendingWorkspaceType, sendIntakeMessage, sendMessage]);

  if (rightPanelCollapsed) return <aside className={`${styles.panel} ${styles.collapsed}`} data-tour="assistant-panel"><button className={styles.expandButton} onClick={toggleRightPanel} title="Open Assistant"><Icon semantic="communication.message" label="Open Assistant" /></button></aside>;

  return (
    <aside className={styles.panel} data-tour="assistant-panel">
      <AssistantHeader title="Assistant" aiState={aiState} toggleRightPanel={toggleRightPanel} />
      {demoMode && (
        <div className={styles.demoBanner}>
          <p className={styles.demoLabel}>Scripted demo mode</p>
          <div className={styles.demoControls}>
            <label htmlFor="assistant-demo-scenario" className={styles.visuallyHidden}>Select demo scenario</label>
            <select id="assistant-demo-scenario" value={demoScenario} onChange={(event) => setDemoScenario(event.target.value as DemoScenarioId)} disabled={demoLoading}>
              {DEMO_SCENARIOS.map((scenario) => <option value={scenario.id} key={scenario.id}>{scenario.label}</option>)}
            </select>
            <button type="button" onClick={() => restartDemoScenario(demoScript)} disabled={demoLoading}>Restart</button>
          </div>
        </div>
      )}
      {context && <ContextBar context={context} contextSyncLabel={context.currentActivityName ?? context.currentStageName ?? context.projectName} />}
      <MessageList messages={messages} aiState={aiState} typingStatus={typingStatus} context={context} onChipClick={handleChipClick} />
      <QuickActions chips={actionChips} onChipClick={handleChipClick} />
      <ChatInput error={assistantError} inputRef={inputRef} onSubmitMessage={handleSubmitMessage} onStartScopeResearch={() => void sendMessage('/research')} />
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
