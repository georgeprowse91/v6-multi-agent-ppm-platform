import { useCallback, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { createArtifact, createEmptyContent, type CanvasType } from '@ppm/canvas-engine';
import { requestJson } from '@/services/apiClient';
import { useAssistantStore } from '@/store/assistant';
import { useCanvasStore } from '@/store/useCanvasStore';
import { useMethodologyStore } from '@/store/methodology';
import { MethodologyMapCanvas } from './MethodologyMapCanvas';
import { ActivityDetailPanel } from './ActivityDetailPanel';

export const canvasMap: Record<string, CanvasType> = {
  document: 'document',
  tree: 'tree',
  timeline: 'timeline',
  spreadsheet: 'spreadsheet',
  dashboard: 'dashboard',
  board: 'board',
  backlog: 'backlog',
  gantt: 'gantt',
  grid: 'grid',
  financial: 'financial',
  dependency_map: 'dependency_map',
  roadmap: 'roadmap',
  approval: 'approval',
  kanban: 'board',
  risk_log: 'grid',
  decision_log: 'approval',
  form: 'grid',
  whiteboard: 'document',
};

export function resolveRuntimeCanvasType(runtimeCanvasType: string | undefined, fallback: CanvasType): CanvasType {
  if (!runtimeCanvasType) return fallback;
  return canvasMap[runtimeCanvasType] ?? fallback;
}

export function MethodologyWorkspaceSurface() {
  const {
    projectMethodology,
    currentActivityId,
    setCurrentActivity,
    getActivity,
    getStageForActivity,
    getAllActivities,
    isStageLockedComputed,
    isActivityLockedComputed,
    resolveNodeRuntime,
    executeNodeAction,
    runtimeActionsAvailable,
    runtimeDefaultViewContract,
    templatesRequiredHere,
    templatesInReview,
    backendReachable,
    reviewQueue,
    loadReviewQueue,
    decideReview,
  } = useMethodologyStore();
  const { openArtifact } = useCanvasStore();
  const navigate = useNavigate();
  const { setActionChips, addAssistantMessage } = useAssistantStore();

  const selectedActivity = currentActivityId ? getActivity(currentActivityId) ?? null : null;
  const selectedStage = currentActivityId ? getStageForActivity(currentActivityId) : undefined;

  useEffect(() => {
    void loadReviewQueue(projectMethodology.projectId);
  }, [loadReviewQueue, projectMethodology.projectId]);

  const prerequisiteNames = useMemo(() => {
    if (!selectedActivity) return [];
    const all = getAllActivities();
    return selectedActivity.prerequisites
      .map((id) => all.find((activity) => activity.id === id))
      .filter((activity) => activity && activity.status !== 'complete')
      .map((activity) => activity!.name);
  }, [getAllActivities, selectedActivity]);

  const publishAssistantContext = useCallback((activityId: string, stageId: string) => {
    const activity = getActivity(activityId);
    if (!activity) return;
    setActionChips(runtimeActionsAvailable
      .filter((event) => ['generate', 'update', 'review', 'approve', 'publish'].includes(event))
      .map((event) => ({
        id: `runtime-${event}`,
        label: event[0].toUpperCase() + event.slice(1),
        category: 'navigate',
        priority: 'high',
        actionType: 'custom',
        payload: { type: 'custom', actionKey: 'methodology_runtime_action', data: { lifecycleEvent: event, stageId, activityId } },
        enabled: true,
      })));
    addAssistantMessage(`Context set: ${activity.name}. Status: ${activity.status.replace('_', ' ')}.`);
  }, [addAssistantMessage, getActivity, runtimeActionsAvailable, setActionChips]);

  const selectActivity = useCallback(async (activityId: string, stageId: string) => {
    setCurrentActivity(activityId);
    await requestJson(`/api/workspace/${encodeURIComponent(projectMethodology.projectId)}/select`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_stage_id: stageId === 'monitoring' ? null : stageId, current_activity_id: activityId, current_canvas_tab: 'document' }),
    });
    await resolveNodeRuntime({ methodologyId: projectMethodology.methodology.id, stageId, activityId, event: 'view' });
    publishAssistantContext(activityId, stageId);
    const selected = getActivity(activityId);
    const isMonitoringDashboard =
      stageId === 'monitoring' &&
      ((selected?.name ?? '').toLowerCase().includes('dashboard') || (selected?.name ?? '').toLowerCase().includes('performance'));
    if (isMonitoringDashboard) {
      navigate(`/projects/${encodeURIComponent(projectMethodology.projectId)}/performance-dashboard`);
    }
  }, [getActivity, navigate, projectMethodology.methodology.id, projectMethodology.projectId, publishAssistantContext, resolveNodeRuntime, setCurrentActivity]);

  const runLifecycleAction = useCallback(async (event: 'generate' | 'update' | 'review' | 'approve' | 'publish', approved = false) => {
    if (!selectedActivity) return;
    if (!backendReachable) {
      addAssistantMessage('Backend unavailable. Runtime actions are disabled until connectivity is restored.');
      return;
    }
    const stageId = selectedStage?.id ?? 'monitoring';
    const response = await executeNodeAction({
      workspaceId: projectMethodology.projectId,
      methodologyId: projectMethodology.methodology.id,
      stageId,
      activityId: selectedActivity.id,
      lifecycleEvent: event,
      userInput: approved ? { human_review_approved: true } : undefined,
    });

    if (response.human_review?.required && response.status === 'review_required') {
      addAssistantMessage('Action submitted and pending human review. Check approvals inbox below.');
      await loadReviewQueue(projectMethodology.projectId);
      return;
    }

    const contract = await resolveNodeRuntime({ methodologyId: projectMethodology.methodology.id, stageId, activityId: selectedActivity.id, event: 'view' });
    const runtimeCanvasType = contract?.canvas?.canvas_type ?? runtimeDefaultViewContract?.canvas?.canvas_type ?? selectedActivity.canvasType;
    const canvasType = resolveRuntimeCanvasType(runtimeCanvasType, selectedActivity.canvasType);
    const ref = ((response.artifacts_updated?.[0] ?? response.artifacts_created?.[0]) ?? {}) as Record<string, unknown>;
    const artifactId = typeof ref.artifact_id === 'string' ? ref.artifact_id : `artifact-${selectedActivity.id}`;
    const title = typeof ref.title === 'string' ? ref.title : selectedActivity.name;
    const opened = createArtifact(canvasType, title, projectMethodology.projectId, createEmptyContent(canvasType));
    openArtifact({ ...opened, id: artifactId, status: event === 'publish' ? 'published' : 'draft', metadata: { ...opened.metadata, runtime: ref.metadata } });
    await requestJson(`/api/workspace/${encodeURIComponent(projectMethodology.projectId)}/select`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_stage_id: stageId === 'monitoring' ? null : stageId,
        current_activity_id: selectedActivity.id,
        current_canvas_tab: canvasType,
      }),
    });
  }, [addAssistantMessage, backendReachable, executeNodeAction, loadReviewQueue, openArtifact, projectMethodology.methodology.id, projectMethodology.projectId, resolveNodeRuntime, runtimeDefaultViewContract?.canvas?.canvas_type, selectedActivity, selectedStage?.id]);

  const onReviewDecision = useCallback(async (approvalId: string, decision: 'approve' | 'reject' | 'modify', notes?: string) => {
    await decideReview({ workspaceId: projectMethodology.projectId, approvalId, decision, notes });
    if (decision === 'approve') {
      await runLifecycleAction('publish', true);
    }
    if (decision === 'modify') {
      await runLifecycleAction('update', true);
    }
  }, [decideReview, projectMethodology.projectId, runLifecycleAction]);

  if (!selectedActivity) {
    return (
      <>
        {!backendReachable && (
          <div role="alert">Backend unavailable. Methodology is in read-only emergency mode.</div>
        )}
      <MethodologyMapCanvas
        stages={projectMethodology.methodology.stages}
        monitoring={projectMethodology.methodology.monitoring}
        currentActivityId={currentActivityId}
        isStageLockedComputed={isStageLockedComputed}
        isActivityLockedComputed={isActivityLockedComputed}
        templatesRequiredHere={templatesRequiredHere}
        templatesInReview={templatesInReview}
        onSelectActivity={(activity, stageId) => { void selectActivity(activity.id, stageId); }}
      />
      </>
    );
  }

  return (
    <>
      {!backendReachable && (
        <div role="alert">Backend unavailable. Runtime actions are disabled.</div>
      )}
    <ActivityDetailPanel
      activity={selectedActivity}
      stageLabel={selectedStage?.id === 'monitoring' ? 'Monitoring & Controlling' : (selectedStage?.name ?? 'Monitoring & Controlling')}
      isLocked={isActivityLockedComputed(selectedActivity.id)}
      missingPrerequisites={prerequisiteNames}
      runtimeActionsAvailable={runtimeActionsAvailable}
      reviewQueue={reviewQueue.filter((item) => item.activity_id === selectedActivity.id || item.stage_id === (selectedStage?.id ?? 'monitoring'))}
      onLifecycleAction={(event) => { void runLifecycleAction(event); }}
      onReviewDecision={(approvalId, decision, notes) => { void onReviewDecision(approvalId, decision, notes); }}
      actionsDisabled={!backendReachable}
    />
    </>
  );
}
